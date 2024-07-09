import os
from openai import OpenAI
import tiktoken
from vertexai.preview import tokenization

import pathlib
import textwrap
import httpx

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

class AIConfigurator:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.initial_prompt = ""
        try:
            with open(os.getenv('INITIAL_PROMPT_FILE_PATH'), "r") as prompt_file:
                self.initial_prompt = prompt_file.read()
        except FileNotFoundError:
            pass
        self.conversation_history = {}
        self.stringified_conversation_history = ""
        self.token_limit = 0 # the maximum number of tokens for a given provider
        self.used_tokens = 0 # keep track of the number of tokens used locally(user + bot combined)
        self.tokens_exceeded = False # flag to keep track of whether the number of used tokens has been exceeded
        self.tokenizer = None # tokenizer for the model being used
        self.active_provider = None

    def set_provider(self, provider_name):
        """Set the active AI provider based on user input."""
        if provider_name.lower() == 'ollama':
            self.active_provider = 'ollama'
            self.token_limit = 8192 # maximum context length
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        elif provider_name.lower() == 'openai' and self.openai_key:
            self.active_provider = 'openai'
            self.token_limit = 16000 # maximum context length(40,000 TPM limit)
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        elif provider_name.lower() == 'gemini' and self.gemini_key:
            self.active_provider = 'gemini'
            self.token_limit = 32000 # for gemini 1.0 pro
            self.tokenizer = tokenization.get_tokenizer_for_model("gemini-1.0-pro")
        else:
            raise ValueError(f"Unsupported AI provider or missing API key: {provider_name}")
    
    def format_history(self) -> str:
        result = ""
        user_queries = self.conversation_history["user"]
        bot_responses = self.conversation_history["bot"]
        threads = list(zip(user_queries, bot_responses))
        for query, response in threads:
            result += f"User: {query}\n"
            result += f"Bot: {response}\n"
        
        return result

    def get_response(self, history, user_message, total_tokens):
        self.tokens_exceeded = False

        self.conversation_history = history
        self.used_tokens = total_tokens
        print(f"Used tokens: {self.used_tokens}")

        is_gpt_provider = self.active_provider in {'openai', 'ollama'}
        query_tokens = len(self.tokenizer.encode(user_message)) if is_gpt_provider else self.tokenizer.count_tokens(user_message)
        print(f"Number of tokens in {user_message}: {query_tokens}")

        if self.conversation_history["user"] and self.conversation_history["bot"]:
            print(f"the conversation history isn't empty")
            if query_tokens + self.used_tokens > self.token_limit:
                print(f"Token limit exceeded")
                self.tokens_exceeded = True
                current = query_tokens + self.used_tokens

                while current > self.token_limit:
                    query = self.conversation_history["user"].pop(0)
                    response = self.conversation_history["bot"].pop(0)
                    q_tokens = len(self.tokenizer.encode(query)) if is_gpt_provider else self.tokenizer.count_tokens(query)
                    res_tokens = len(self.tokenizer.encode(response)) if is_gpt_provider else self.tokenizer.count_tokens(response)
                    current -= (q_tokens + res_tokens)
                    self.used_tokens -= (q_tokens + res_tokens)

                # reconstruct stringified conversation history based on truncated version
                self.stringified_conversation_history = self.format_history()
                print(f"Conversation history: {self.stringified_conversation_history}")

            else: # we can just update the number of used tokens since it's within limits
                print(f"Tokens used is under the limit")
                self.stringified_conversation_history += f"User: {self.conversation_history['user'][-1]}\n"
                self.stringified_conversation_history += f"Bot: {self.conversation_history['bot'][-1]}\n"
                print(f"Conversation history: {self.stringified_conversation_history}")
            
        else:
            # reset conversation history, used tokens, and whether tokens have been exceeded when page is refreshed or very first time when conversation is started
            self.conversation_history = {}
            self.stringified_conversation_history = ""
            self.used_tokens = 0
            self.tokens_exceeded = False
        
        self.used_tokens += query_tokens # update used tokens with token count for current user query
        result = {"response": "", "usedTokens": self.used_tokens, "updatedHistory": self.conversation_history if self.tokens_exceeded else None}

        if self.active_provider in {'openai', 'ollama'}:
            response =  self._get_response_from_openai(user_message)
            result["response"] = response
            result["usedTokens"] += len(self.tokenizer.encode(response))
            return result
        elif self.active_provider == 'gemini':
            response = self._get_response_from_gemini(user_message)
            result["response"] = response
            result["usedTokens"] += self.tokenizer.count_tokens(response)
            return result
        else:
            raise ValueError("No AI service configured.")
    
    def _get_response_from_openai(self, user_message):
        # this is default openai data
        model = "gpt-3.5-turbo-0125"
        client = OpenAI(
            api_key=self.openai_key
        )

        if self.active_provider.lower() == 'ollama':
            model = "llama3"
            client = OpenAI(
                api_key="ollama",
                base_url='http://localhost:11434/v1/'
            )
        
        # including conversation history along with query only if it isn't empty
        if self.stringified_conversation_history:
            user_message = self.stringified_conversation_history + user_message

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.initial_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                n=1,
                temperature=0.5,
                stop=None
            )

            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise e 
            
    def _get_response_from_gemini(self, user_message):        
        model = genai.GenerativeModel('gemini-1.0-pro')
        genai.configure(api_key=self.gemini_key)

        prompt = self.initial_prompt
        prompt += (self.stringified_conversation_history + user_message)
        
        response = model.generate_content(prompt)

        # Extract the response text
        return response.text
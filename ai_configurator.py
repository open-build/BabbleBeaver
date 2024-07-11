import os
from openai import OpenAI
import tiktoken # for usage with openai models
from vertexai.preview import tokenization # for usage with gemini models
from tokenizers import Tokenizer # for usage with ollama and models served via hugging face

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
        self.hf_key = os.getenv('HUGGINGFACE_AUTH_TOKEN')
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
            self.tokenizer = Tokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B", auth_token=self.hf_key)
        elif provider_name.lower() == 'openai' and self.openai_key:
            self.active_provider = 'openai'
            self.token_limit = 16385 # maximum context length(40,000 TPM limit)
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
        
        if not user_queries and not bot_responses:
            return ""
        
        threads = list(zip(user_queries, bot_responses))
        for query, response in threads:
            result += f"User: {query}\n"
            result += f"Bot: {response}\n"
        
        return result

    def retrieve_response_and_tokens(self, message, fetch_response=False):
        response = ""
        tokens = 0
        # if the flag is set to true, tokenize the response otherwise tokenize the query
        if self.active_provider == "openai":
            response = self._get_response_from_openai(message)
            tokens =  len(self.tokenizer.encode(response)) if fetch_response else len(self.tokenizer.encode(message))
        elif self.active_provider == "ollama":
            response = self._get_response_from_openai(message)
            tokens =  len(self.tokenizer.encode(response).ids) if fetch_response else len(self.tokenizer.encode(message).ids)
        elif self.active_provider == "gemini":
            response = self._get_response_from_gemini(message)
            tokens =  len(self.tokenizer.count_tokens(response)) if fetch_response else len(self.tokenizer.count_tokens(message))
        else:
            raise ValueError("No AI service configured.")
        
        return {"response": response if fetch_response else None, "tokens": tokens}

    def get_response(self, history, user_message, total_tokens):
        self.tokens_exceeded = False

        self.conversation_history = history
        self.used_tokens = total_tokens
        # print(f"conversation history being passed in: {self.conversation_history}")
        print(f"Tokens used so far received from client: {self.used_tokens}")

        # won't return any response
        query_tokens = self.retrieve_response_and_tokens(user_message)["tokens"]
        print(f"Number of tokens in \"{user_message}\": {query_tokens}")

        if self.conversation_history["user"] and self.conversation_history["bot"]:
            if query_tokens + self.used_tokens >= self.token_limit:
                self.tokens_exceeded = True
                current = query_tokens + self.used_tokens

                # on each iteration we need to account for the history tokens as well in addition to query and response tokens(only applicable for values starting index 1 since history is being passed for all of them)
                
                index = 0
                previous_thread = ""
        
                while current >= self.token_limit:
                    query = self.conversation_history["user"].pop(0)
                    response = self.conversation_history["bot"].pop(0)
            
                    q_tokens = self.retrieve_response_and_tokens(query)["tokens"]
                    res_tokens = self.retrieve_response_and_tokens(response)["tokens"]
                    history_tokens = self.retrieve_response_and_tokens(previous_thread)["tokens"] if index > 0 else 0

                    current -= (history_tokens + q_tokens + res_tokens)
                    self.used_tokens -= (history_tokens + q_tokens + res_tokens)

                    index += 1
                    previous_thread = f"User: {query}\nBot: {response}\n"

                # reconstruct stringified conversation history based on truncated version
                self.stringified_conversation_history = self.format_history()
                print(f"Conversation history: {self.stringified_conversation_history}")

            else: # we can just update the number of used tokens since it's within limits
                self.stringified_conversation_history += f"User: {self.conversation_history['user'][-1]}\n"
                self.stringified_conversation_history += f"Bot: {self.conversation_history['bot'][-1]}\n"

                # include context being passed in also in used token count
                self.used_tokens += self.retrieve_response_and_tokens(self.stringified_conversation_history)["tokens"]
                print(f"tokens used after including conversation history: {self.used_tokens}")
        else:
            # reset conversation history, used tokens, and whether tokens have been exceeded when page is refreshed or very first time when conversation is started
            # print(f"page was either refreshed or history passed in is empty")
            self.conversation_history = {}
            self.stringified_conversation_history = ""
            self.used_tokens = 0
            self.tokens_exceeded = False
        
        self.used_tokens += query_tokens # update used tokens with token count for current user query
        print(f"tokens used for the current query(question + history combined): {self.used_tokens}")

        result = self.retrieve_response_and_tokens(user_message, True)
        print(f"tokens used for the response: {result['tokens']}")
        self.used_tokens += result["tokens"]

        return {"response": result["response"], "usedTokens": self.used_tokens, "updatedHistory": self.conversation_history if self.tokens_exceeded else None}
    
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
        
        print("convo history")
        print(self.stringified_conversation_history)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.initial_prompt},
                    {"role": "user", "content": self.stringified_conversation_history + user_message}
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
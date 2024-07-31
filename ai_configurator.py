import os
import configparser

from openai import OpenAI
import google.generativeai as genai

import tiktoken # for usage with openai models
from vertexai.preview import tokenization # for usage with gemini models
from tokenizers import Tokenizer # for usage with ollama models

import pathlib
import textwrap
import httpx

from IPython.display import display
from IPython.display import Markdown
class AIConfigurator:
    def __init__(self):
        # loading in API keys
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.hf_key = os.getenv('HUGGINGFACE_AUTH_TOKEN')

        # loading in configuration file
        self.config = configparser.ConfigParser()
        self.config.read("model_config.ini")
        self.available_models = list(self.config.sections())

        # loading in context
        self.initial_prompt = ""
        try:
            with open(os.getenv('INITIAL_PROMPT_FILE_PATH'), "r") as prompt_file:
                self.initial_prompt = prompt_file.read()
        except FileNotFoundError:
            pass
        
        # variables related to keeping track of conversation history and token usage
        self.conversation_history = {} # the history received from the client each time and to be used for truncation
        self.stringified_conversation_history = "" # to be passed in along with the query each time
        self.token_limit = 0 # the maximum number of tokens for a given provider
        self.used_tokens = 0 # keep track of the number of tokens used locally(user + bot combined)
        self.tokens_exceeded = False # flag to keep track of whether the number of used tokens has been exceeded
        self.tokenizer = None # tokenizer for the model being used
        self.previous_thread = ""

        # the provider and the model being used
        self.active_provider = None
        self.active_model = None

    def set_model(self, model_name):
        """Set the active AI provider based on user input."""
        match_found = False
        for model in self.available_models:
            if model == model_name:
                self.active_model = model
                match_found = True
                self.token_limit = self.config[model]["context_length"]
                if "model_id" not in self.config[model]: # gpt/gemini model
                    is_openai = model.startswith("gpt")
                    self.active_provider = "openai" if is_openai else "gemini"
                    self.tokenizer = tiktoken.get_encoding("cl100k_base") if is_openai else tokenization.get_tokenizer_for_model(model)
                else: # ollama model
                    self.active_provider = "ollama"
                    self.tokenizer = Tokenizer.from_pretrained(self.config[model]["model_id"], auth_token=self.hf_key)
                break
        
        if not match_found:
            raise ValueError(f"Unsupported model or missing API key: {model_name}")
    
    def format_history(self) -> str:
        result = ""
        user_queries = self.conversation_history["user"]
        bot_responses = self.conversation_history["bot"]
        
        threads = list(zip(user_queries, bot_responses))
        for query, response in threads:
            result += f"User: {query}\nBot: {response}\n"
        
        return result

    def retrieve_response_and_tokens(self, message, fetch_response=False):
        response = None
        if fetch_response:
            response = self._get_response_from_openai(message) if self.active_provider in {'openai', 'ollama'} else self._get_response_from_gemini(message)
        tokens = 0
        # if the flag is set to true, tokenize the response otherwise tokenize the query
        if self.active_provider == "openai":
            tokens =  len(self.tokenizer.encode(response)) if fetch_response else len(self.tokenizer.encode(message))
        elif self.active_provider == "ollama":
            tokens =  len(self.tokenizer.encode(response).ids) if fetch_response else len(self.tokenizer.encode(message).ids)
        elif self.active_provider == "gemini":
            tokens = self.tokenizer.count_tokens(response).total_tokens if fetch_response else self.tokenizer.count_tokens(message).total_tokens
        else:
            raise ValueError("No AI service configured.")
        
        return {"response": response, "tokens": tokens}

    def get_response(self, history, user_message, total_tokens):
        self.tokens_exceeded = False

        self.conversation_history = history
        self.used_tokens = total_tokens

        query_tokens = self.retrieve_response_and_tokens(user_message)["tokens"]

        if self.conversation_history["user"] and self.conversation_history["bot"]:
            if query_tokens + self.used_tokens >= self.token_limit:
                self.tokens_exceeded = True
                current = query_tokens + self.used_tokens
        
                while current >= self.token_limit:
                    query = self.conversation_history["user"].pop(0)
                    response = self.conversation_history["bot"].pop(0)
            
                    q_tokens = self.retrieve_response_and_tokens(query)["tokens"]
                    res_tokens = self.retrieve_response_and_tokens(response)["tokens"]
                    history_tokens = self.retrieve_response_and_tokens(self.previous_thread)["tokens"] if self.previous_thread else 0

                    current -= (history_tokens + q_tokens + res_tokens)
                    self.used_tokens -= (history_tokens + q_tokens + res_tokens)

                    # accumulate the history across various runs
                    self.previous_thread += f"User: {query}\nBot: {response}\n"

                # reconstruct stringified conversation history based on truncated version
                self.stringified_conversation_history = self.format_history()

            else: # we can just update the number of used tokens since it's within limits
                self.stringified_conversation_history += f"User: {self.conversation_history['user'][-1]}\n"   
                self.stringified_conversation_history += f"Bot: {self.conversation_history['bot'][-1]}\n"

                # include context being passed in also in used token count
                self.used_tokens += self.retrieve_response_and_tokens(self.stringified_conversation_history)["tokens"]
        else:
            # reset history each time the page is refreshed(start of a new conversation)
            self.conversation_history = {}
            self.stringified_conversation_history = ""
            self.previous_thread = ""
            self.used_tokens = 0
            self.tokens_exceeded = False
        
        self.used_tokens += query_tokens # update used tokens with token count for current user query

        result = self.retrieve_response_and_tokens(user_message, True)
        self.used_tokens += result["tokens"]

        return {"response": result["response"], "usedTokens": self.used_tokens, "updatedHistory": self.conversation_history if self.tokens_exceeded else None}
    
    def _get_response_from_openai(self, user_message):
        # print(f"Active provider: {self.active_provider}")
        # print(f"Active model: {self.active_model}")

        # this is default openai data
        primary_model = self.active_model
        client = OpenAI(
            api_key=self.openai_key
        )

        if self.active_provider == 'ollama':
            client = OpenAI(
                api_key="ollama",
                base_url='http://localhost:11434/v1/'
            )

        try:
            response = client.chat.completions.create(
                model=primary_model,
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
        model = genai.GenerativeModel(self.active_model)

        # gemini-1.0-pro doesn't support system instructions
        if self.active_model != "gemini-pro":
             model = genai.GenerativeModel(self.active_model, system_instruction=self.initial_prompt)

        genai.configure(api_key=self.gemini_key)

        prompt = self.stringified_conversation_history + user_message
        
        response = model.generate_content(prompt)

        # Extract the response text
        return response.text
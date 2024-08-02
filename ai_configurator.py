import os
import importlib
import inspect
from typing import Dict, List, Optional
class AIConfigurator:
    def __init__(self):
        # will hold the current model instance
        self.current_model_instance = None  

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
        self.previous_thread = ""

        # keep track of current model and provider
        self.active_provider_name = ""
        self.active_model_name = ""

    def set_model(self, provider: str, model_name: str) -> None:
        """Set the active AI provider based on user input."""
        # we will only execute this whenever the provider and/or the model name is changed
        if provider != self.active_provider_name or model_name != self.active_model_name:
            try:
                module_name = f"model-config.{provider}.{provider}-config"
                module = importlib.import_module(module_name)
                classes = inspect.getmembers(module, inspect.isclass)
                classes = list(filter(lambda x: x[1].__module__ == module_name, classes))

                _, target_class = classes[0]

                self.current_model_instance = target_class(model_name)
                model_info = self.current_model_instance.get_model_info()

                self.active_provider_name = model_info[0]
                self.active_model_name = model_info[1]
                self.token_limit = int(model_info[2])

            except ModuleNotFoundError:
                raise ModuleNotFoundError(f"The model-config directory is either non-existent or a configuration file hasn't been created for {provider} in the same directory. Please try again!")
    
    def format_history(self) -> str:
        result = ""
        user_queries = self.conversation_history["user"]
        bot_responses = self.conversation_history["bot"]
        
        threads = list(zip(user_queries, bot_responses))
        for query, response in threads:
            result += f"User: {query}\nBot: {response}\n"
        
        return result

    def retrieve_response_and_tokens(self, message: str, fetch_response=False) -> Dict[Optional[str], int]:
        response, tokens = None, None
        if fetch_response:
            response = self.get_model_completion(message)
            tokens = self.current_model_instance.tokenize(response)
        else:
            # just tokenize the query if fetch_response is false
            tokens = self.current_model_instance.tokenize(message)

        return {"response": response, "tokens": tokens}

    def get_response(self, history: Dict[List[str], List[str]], user_message: str, total_tokens: int):
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
    
    def get_model_completion(self, user_message: str) -> str:
        return self.current_model_instance.get_completion(
            self.initial_prompt,
            user_message,
            self.stringified_conversation_history
        )
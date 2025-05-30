import os # not explicitly used but needs to be present
from dotenv import load_dotenv
from configparser import ConfigParser

load_dotenv()
    
parser = ConfigParser()

class ModelConfig():
    def __init__(self, provider_name, model_name, tokenizer, completion, use_initial_prompt):
        self.default_max_tokens = 300
        self.default_temperature = 0.5

        self.API_KEY = None
        self.context_length = None
        self.active_provider = None
        self.active_model = None

        self.tokenizer_func = tokenizer
        self.completion_func = completion

        self.use_initial_prompt = use_initial_prompt
        
        model_match_found = False
        parser.read("model_config/model_config.ini")
        self.available_models = list(parser.sections())

        if not self.available_models:
            raise ValueError("You haven\'t specified any models in the configuration file!")
            
        for model in self.available_models:

            provider = parser[model]["provider"]

            # if the model specified in the config file matches the model passed in as a param
            if model == model_name:
                # if the provider specified in the config file matches the provider passed in as a param
                if provider == provider_name:
                    model_match_found = True

                    # updating the current provider and model
                    self.active_provider = provider_name
                    self.active_model = model_name

                    properties = parser[model] # extracting this matched model's properties

                    # updating model completion parameters if existent
                    if "max_output_tokens" in properties:
                        self.default_max_tokens = int(properties["max_output_tokens"])
                    if "temperature" in properties:
                        self.default_temperature = float(properties["temperature"])
                        
                    # updating API key if existent
                    if "api_key" not in properties:
                        raise ValueError(f"A key with the name of \"api_key\" must be supplied for {model_name}")
                    else:
                        try:
                            self.API_KEY = eval(properties["api_key"])
                        except NameError:  
                            self.API_KEY = properties["api_key"]
                        
                    # updating context window if it exists
                    if "context_length" not in properties:
                        raise ValueError(f"A key with the name of \"context_length\" must be supplied for {model_name}")
                    else:
                        self.context_length = int(properties["context_length"])
                        
                    break
                
                # we found a matching model but the provider doesn't match
                else:
                    raise ValueError(f"{model_name} isn't supported for {provider_name}. Please select another one and try again.")

        # the model itself is non-existent  
        if not model_match_found:
            raise ValueError(f"{model_name} is non-existent. Please select a different one and try again.")

    def get_model_info(self):
        return [self.active_provider, self.active_model, self.context_length]

    def tokenize(self, text: str) -> int:
        if self.tokenizer_func:
            return self.tokenizer_func(text)
        raise ValueError(f"Make sure that you've provided a tokenizer for {self.model}")

    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str) -> str:
        try:
            return self.completion_func(
                self.API_KEY,
                initial_prompt if self.use_initial_prompt else None,
                user_message,
                conversation_history,
                self.default_max_tokens,
                self.default_temperature,
                self.active_model
            )
        except Exception as e:
            raise e
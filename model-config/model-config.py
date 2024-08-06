import os
from dotenv import load_dotenv
from configparser import ConfigParser

load_dotenv()
parser = ConfigParser()

class ModelConfig():
    parser.read("model-config/model-config.ini")
    models = list(parser.sections())

    def __init__(self, provider_name, model_name):
        self.max_tokens = 300
        self.temperature = 0.5
        self.API_KEY = None
        self.context_length = None
        self.provider = None
        self.model = None
        self.tokenizer = None
        
        model_match_found = False
        if not self.models:
            raise ValueError("You haven\'t specified any models in the configuration file!")
        else:
            for model in self.models:
                provider = parser[model]["provider"]
                if model == model_name and provider == provider_name:
                    model_match_found = True

                    self.provider = provider_name
                    self.model = model_name

                    properties = parser[model]

                    # updating model completion parameters if existent
                    if "max_output_tokens" in properties:
                        self.max_tokens = int(properties["max_output_tokens"])
                    if "temperature" in properties:
                        self.temperature = float(properties["temperature"])
                    
                    # updating API key if existent
                    if "api_key" not in properties:
                        raise ValueError(f"A key with the name of \"api_key\" must be supplied for {model_name}")
                    else:
                        self.API_KEY = properties["api_key"]
                    
                    # updating context window if it exists
                    if "context_length" not in properties:
                        raise ValueError(f"A key with the name of \"context_length\" must be supplied for {model_name}")
                    else:
                        self.context_length = int(properties["context_length"])
                    
                    # updating tokenizer if it exists
                    if "tokenizer_import" not in properties and "tokenizer_definition" not in properties:
                        raise ValueError(f"A key with the name \"tokenizer_import\" and a key with the name \"tokenizer_definition\" must be specified for {model_name}")
                    else:
                        exec(properties["tokenizer_import"], globals())
                        compiled = compile(properties["tokenizer_definition"], "<string>", "eval")
                        self.tokenizer = eval(compiled)
                    
                    break

                elif provider != provider_name:
                    raise ValueError(f"{model_name} isn't supported for {provider_name}. Please select another one and try again.")
            
            if not model_match_found:
                raise ValueError(f"{model_name} is non-existent. Please select a different one and try again.")

    def get_model_info(self):
        return [self.provider, self.model, self.context_length]

    def tokenize(self, text: str) -> int:
        return self.tokenizer(text)

    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str) -> str:
        pass

if __name__ == "__main__":
    cl = ModelConfig("openai", "gpt-3.5-turbo")
    print(f"api key: {cl.API_KEY}")
    print(f"context: {cl.context_length}")
    print(f"provider: {cl.provider}")
    print(f"model: {cl.model}")
    print(f"model info: {cl.get_model_info()}")
    print(f"number of tokens in \"hello world\": {cl.tokenize('hello world')}")
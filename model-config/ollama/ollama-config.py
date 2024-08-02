from tokenizers import Tokenizer
import os
from dotenv import load_dotenv
from openai import OpenAI
from configparser import ConfigParser

load_dotenv()
parser = ConfigParser()

class OllamaConfig():
    def __init__(self, selected_model):
        self.API_KEY = "ollama"
        self.AUTH_TOKEN = os.getenv("HUGGINGFACE_AUTH_TOKEN")
        self.client = OpenAI(api_key=self.API_KEY, base_url='http://localhost:11434/v1/')

        parser.read("model-config/ollama/ollama-config.ini")
        self.sections = list(parser.sections())
        self.MODELS = dict(zip(self.sections, [[parser[model]["context_length"], parser[model]["model_id"]] for model in self.sections]))
        self.provider = "ollama"

        self.selected_model = selected_model
        if self.selected_model not in self.MODELS:
            raise ValueError(f"{selected_model} isn't supported for {self.provider}. Please select another one and try again")
        
        self.tokenizer = Tokenizer.from_pretrained(self.MODELS[self.selected_model][1], auth_token=self.AUTH_TOKEN)
    
    def get_model_info(self):
        return [self.provider, self.selected_model, self.MODELS[self.selected_model][0]]
    
    def tokenize(self, text) -> int:
        return len(self.tokenizer.encode(text).ids)
    
    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str):
        try:
            response = self.client.chat.completions.create(
                model=self.selected_model,
                messages=[
                    {"role": "system", "content": initial_prompt},
                    {"role": "user", "content": conversation_history + user_message}
                ],
                max_tokens=300,
                n=1,
                temperature=0.5,
                stop=None
            )

            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise e
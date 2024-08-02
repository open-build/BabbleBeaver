import os
from dotenv import load_dotenv
import tiktoken
from openai import OpenAI
from configparser import ConfigParser

load_dotenv()
parser = ConfigParser()

class OpenAIConfig():
    def __init__(self, selected_model):
        self.API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.API_KEY)

        parser.read("model-config/openai/openai-config.ini")
        self.sections = list(parser.sections())
        self.MODELS = dict(zip(self.sections, [parser[model]["context_length"] for model in self.sections]))
        self.provider = "openai"

        self.selected_model = selected_model
        if self.selected_model not in self.MODELS:
            raise ValueError(f"{selected_model} isn't supported for {self.provider}. Please select another one and try again")
        
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def get_model_info(self):
        return [self.provider, self.selected_model, self.MODELS[self.selected_model]]

    def tokenize(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

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
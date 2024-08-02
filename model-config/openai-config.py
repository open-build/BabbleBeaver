import os
from dotenv import load_dotenv
import tiktoken
from openai import OpenAI

load_dotenv()

class OpenAIConfig():
    def __init__(self, selected_model):
        self.API_KEY = os.getenv("OPENAI_API_KEY")
        self.MODELS = {
            "gpt-3.5-turbo": [16385],
            "gpt-3.5-turbo-1106": [16385],
            "gpt-4-turbo-preview": [128000],
            "gpt-4-turbo": [128000],
            "gpt-4o-mini": [128000]
        }
        self.selected_model = selected_model
        if self.selected_model not in self.MODELS:
            raise ValueError(f"{selected_model} is not available. Please select another one and try again")
        self.provider = "openai"
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def get_model_info(self):
        return [self.provider, self.selected_model, self.MODELS[self.selected_model][0]]

    def tokenize(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str):
        client = OpenAI(api_key=self.API_KEY)

        try:
            response = client.chat.completions.create(
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
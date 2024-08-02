import os
from dotenv import load_dotenv
from google.generativeai import GenerativeModel, configure, GenerationConfig
from vertexai.preview import tokenization
from configparser import ConfigParser

load_dotenv()
parser = ConfigParser()

class GeminiConfig():
    def __init__(self, selected_model):
        self.API_KEY = os.getenv("GOOGLE_API_KEY")
        configure(api_key=self.API_KEY)

        parser.read("model-config/gemini/gemini-config.ini")
        self.sections = list(parser.sections())
        self.MODELS = dict(zip(self.sections, [parser[model]["context_length"] for model in self.sections]))
        self.provider = "gemini"

        self.selected_model = selected_model
        if self.selected_model not in self.MODELS:
            raise ValueError(f"{selected_model} isn't supported for {self.provider}. Please select another one and try again")
        
        self.client = GenerativeModel(self.selected_model)
        
        self.tokenizer = tokenization.get_tokenizer_for_model(self.selected_model)
    
    def get_model_info(self):
        return [self.provider, self.selected_model, self.MODELS[self.selected_model]]
    
    def tokenize(self, text: str) -> int:
        return self.tokenizer.count_tokens(text).total_tokens
    
    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str):
        # gemini-1.0-pro doesn't support system instructions
        if self.selected_model != "gemini-1.0-pro":
             self.client = GenerativeModel(self.selected_model, system_instruction=initial_prompt)

        prompt = conversation_history + user_message
        
        response = self.client.generate_content(prompt, generation_config=GenerationConfig(
            max_output_tokens=300,
            temperature=0.5
        ))

        # Extract the response text
        return response.text
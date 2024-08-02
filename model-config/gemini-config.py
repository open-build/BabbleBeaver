import os
from dotenv import load_dotenv
import google.generativeai as genai
from vertexai.preview import tokenization

load_dotenv()

class GeminiConfig():
    def __init__(self, selected_model):
        self.API_KEY = os.getenv("GOOGLE_API_KEY")
        self.MODELS = {
            "gemini-1.0-pro": [32000],
            "gemini-1.5-pro": [2000000],
            "gemini-1.5-flash": [1000000]
        }
        self.selected_model = selected_model
        if self.selected_model not in self.MODELS:
            raise ValueError(f"{selected_model} is not available. Please select another one and try again")
        self.provider = "gemini"
        self.tokenizer = tokenization.get_tokenizer_for_model(self.selected_model)
    
    def get_model_info(self):
        return [self.provider, self.selected_model, self.MODELS[self.selected_model][0]]
    
    def tokenize(self, text: str) -> int:
        return self.tokenizer.count_tokens(text).total_tokens
    
    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str):
        model = genai.GenerativeModel(self.selected_model)

        # gemini-1.0-pro doesn't support system instructions
        if self.selected_model != "gemini-1.0-pro":
             model = genai.GenerativeModel(self.selected_model, system_instruction=initial_prompt)

        genai.configure(api_key=self.API_KEY)

        prompt = conversation_history + user_message

        config = genai.GenerationConfig(
            candidate_count=1, stop_sequences=None, max_output_tokens=300, temperature=-0.5
        )
        
        response = model.generate_content(prompt, generation_config=config)

        # Extract the response text
        return response.text
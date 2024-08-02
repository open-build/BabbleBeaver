from tokenizers import Tokenizer
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class OllamaConfig():
    def __init__(self, selected_model):
        self.API_KEY = "ollama"
        self.AUTH_TOKEN = os.getenv("HUGGINGFACE_AUTH_TOKEN")
        self.MODELS = {
            "llama3.1": [128000, "meta-llama/Meta-Llama-3.1-8B-Instruct"],
            "llama3.1:70b": [128000, "meta-llama/Meta-Llama-3.1-70B-Instruct"],
            "gemma2": [8192, "google/gemma-2-9b-it"],
            "gemma2:27b": [8192, "google/gemma-2-27b-it"],
            "mistral-nemo": [128000, "mistralai/Mistral-Nemo-Instruct-2407"],
            "mistral-large": [128000, "mistralai/Mistral-Large-Instruct-2407"],
            "qwen2": [131072, "Qwen/Qwen2-7B-Instruct"],
            "qwen2:72b": [131072, "Qwen/Qwen2-72B-Instruct"],
            "phi3": [128000, "microsoft/Phi-3-mini-128k-instruct"],
            "phi3:14b": [128000, "microsoft/Phi-3-medium-128k-instruct"],
            "mistral": [32000, "mistralai/Mistral-7B-Instruct-v0.2"],
            "mixtral": [32000, "mistralai/Mixtral-8x7B-Instruct-v0.1"],
            "mixtral:8x22b": [64000, "mistralai/Mixtral-8x22B-Instruct-v0.1"],
            "codegemma": [8192, "google/codegemma-7b"],
            "command-r": [128000, "CohereForAI/c4ai-command-r-v01"],
            "command-r-plus": [128000, "CohereForAI/c4ai-command-r-plus"],
            "llama3": [8192, "meta-llama/Meta-Llama-3-8B-Instruct"],
            "llama3:70b": [8192, "meta-llama/Meta-Llama-3-70B-Instruct"],
            "gemma": [8192, "google/gemma-1.1-7b-it"],
            "gemma:2b": [8192, "google/gemma-1.1-2b-it"],
            "llama2": [4096, "meta-llama/Llama-2-7b-chat-hf"],
            "llama2:13b": [4096, "meta-llama/Llama-2-13b-chat-hf"],
            "llama2:70b": [4096, "meta-llama/Llama-2-70b-chat-hf"],
            "codellama": [16000, "codellama/CodeLlama-7b-Instruct-hf"],
            "codellama:13b": [16000, "codellama/CodeLlama-13b-Instruct-hf"],
            "codellama:34b": [16000, "codellama/CodeLlama-34b-Instruct-hf"],
            "codellama:70b": [16000, "codellama/CodeLlama-70b-Instruct-hf"]
        }
        self.selected_model = selected_model
        if self.selected_model not in self.MODELS:
            raise ValueError(f"{selected_model} is not available. Please select another one and try again")
        self.provider = "ollama"
        self.tokenizer = Tokenizer.from_pretrained(self.MODELS[self.selected_model][1], auth_token=self.AUTH_TOKEN)
    
    def get_model_info(self):
        return [self.provider, self.selected_model, self.MODELS[self.selected_model][0]]
    
    def tokenize(self, text) -> int:
        return len(self.tokenizer.encode(text).ids)
    
    def get_completion(self, initial_prompt: str, user_message: str, conversation_history: str):
        client = OpenAI(api_key=self.API_KEY, base_url='http://localhost:11434/v1/')

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

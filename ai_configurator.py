import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from model_config.model_config import ModelConfig
import openai  # Ensure this is installed and available

load_dotenv()

class AIConfigurator:
    def __init__(self):
        # Holds the current model instance
        self.current_model_instance = None  

        # Load initial prompt from file
        self.initial_prompt = ""
        prompt_file_path = os.getenv('INITIAL_PROMPT_FILE_PATH')
        if prompt_file_path:
            try:
                with open(prompt_file_path, "r") as prompt_file:
                    self.initial_prompt = prompt_file.read()
            except FileNotFoundError:
                pass
        
        # Variables related to conversation history and token usage
        self.conversation_history = {"user": [], "bot": []}  # Ensure default structure
        self.stringified_conversation_history = ""  # Passed along with queries
        self.token_limit = 0  # Max tokens allowed by provider
        self.used_tokens = 0  # Track user + bot token usage
        self.tokens_exceeded = False  # Flag if token limit is exceeded
        self.previous_thread = ""

        # Track current model and provider
        self.active_provider_name = ""
        self.active_model_name = ""

    def set_model(self, provider_name: str, model_name: str, tokenizer_func, completion_func, use_initial_prompt: bool) -> None:
        """Set the active AI provider and model if changed."""
        if provider_name != self.active_provider_name or model_name != self.active_model_name:
            try:
                self.current_model_instance = ModelConfig(provider_name, model_name, tokenizer_func, completion_func, use_initial_prompt)
                model_info = self.current_model_instance.get_model_info()

                self.active_provider_name, self.active_model_name, self.token_limit = model_info
            except Exception as e:
                raise ValueError(f"Failed to set model: {e}")

    def get_response(self, user_message: str):
        """Route the request to the correct AI provider."""
        if self.active_provider_name == 'openai':
            return self._get_response_from_openai(user_message)
        elif self.active_provider_name == 'gemini':
            return self._get_response_from_gemini(user_message)
        else:
            raise ValueError("No AI service configured.")

    def _get_response_from_openai(self, user_message: str) -> str:
        """Generate a response using OpenAI API."""
        openai.api_key = os.getenv("OPENAI_API_KEY")  # Ensure the API key is set
        prompt = f"""
        The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
        {user_message}
        """
        try:
            response = openai.Completion.create(
                engine="davinci",  
                prompt=prompt,
                max_tokens=300,
                n=1,
                stop=None,
                temperature=0.5
            )
            return response.choices[0].text.strip()
        except Exception as e:
            return f"Error communicating with OpenAI: {e}"

    def _get_response_from_gemini(self, user_message: str) -> str:
        """Generate a response using Gemini AI (stubbed)."""
        try:
            # Placeholder for Gemini API call
            return f"Gemini response for: {user_message}"
        except ValueError as e:
            return f"Error: {e}"

    def format_history(self) -> str:
        """Format conversation history into a string."""
        result = ""
        for query, response in zip(self.conversation_history["user"], self.conversation_history["bot"]):
            result += f"User: {query}\nBot: {response}\n"
        return result

    def retrieve_response_and_tokens(self, message: str, fetch_response: bool = False) -> Dict[Optional[str], int]:
        """Retrieve a response and its token count."""
        tokens = self.current_model_instance.tokenize(message)
        response = self.get_model_completion(message) if fetch_response else None
        return {"response": response, "tokens": tokens}

    def process_response(self, history: Dict[s

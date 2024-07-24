import os
import openai

import pathlib
import textwrap

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

class AIConfigurator:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.active_provider = None

    def set_provider(self, provider_name):
        """Set the active AI provider based on user input."""
        if provider_name.lower() == 'openai' and self.openai_key:
            self.active_provider = 'openai'
        elif provider_name.lower() == 'gemini' and self.gemini_key:
            self.active_provider = 'gemini'
        else:

            raise ValueError(f"Unsupported AI provider or missing API key: {provider_name}")

    def get_response(self, user_message):
        if self.active_provider == 'openai':
            return self._get_response_from_openai(user_message)
        elif self.active_provider == 'gemini':
            return self._get_response_from_gemini(user_message)
        else:
            raise ValueError("No AI service configured.")

    def _get_response_from_openai(self, user_message):
        openai.api_key = self.openai_key
        prompt = f"""
        The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
        {user_message}
        """
        response = openai.Completion.create(
            engine="davinci",  # Assuming using Davinci model here
            prompt=prompt,
            max_tokens=300,
            n=1,
            stop=None,
            temperature=0.5
        )
        return response.choices[0].text.strip()
    
            
    def _get_response_from_gemini(self, user_message):

        GOOGLE_API_KEY = self.gemini_key
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        genai.configure(api_key=GOOGLE_API_KEY)
        prompt = user_message
        
        response = model.generate_content(prompt)

        # Extract the response text
        return response.text

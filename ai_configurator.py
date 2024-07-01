import os
from openai import OpenAI

import pathlib
import textwrap
import httpx

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

class AIConfigurator:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.initial_prompt = ""
        try:
            with open(os.getenv('INITIAL_PROMPT_FILE_PATH'), "r") as prompt_file:
                self.initial_prompt = prompt_file.read()
        except FileNotFoundError:
            pass
        self.active_provider = None

    def set_provider(self, provider_name):
        """Set the active AI provider based on user input."""
        if provider_name.lower() == 'ollama':
            self.active_provider = 'ollama'
        elif provider_name.lower() == 'openai' and self.openai_key:
            self.active_provider = 'openai'
        elif provider_name.lower() == 'gemini' and self.gemini_key:
            self.active_provider = 'gemini'
        else:
            raise ValueError(f"Unsupported AI provider or missing API key: {provider_name}")

    def get_response(self, user_message):
        if self.active_provider in {'openai', 'ollama'}:
            return self._get_response_from_openai(user_message)
        elif self.active_provider == 'gemini':
            return self._get_response_from_gemini(user_message)
        else:
            raise ValueError("No AI service configured.")
    
    def _get_response_from_openai(self, user_message):
        # this is default openai data
        model = "gpt-3.5-turbo-0125"
        client = OpenAI(
            api_key=self.openai_key
        )

        if self.active_provider.lower() == 'ollama':
            model = "llama3"   # config?
            client = OpenAI(
                api_key="ollama",
                base_url='http://localhost:11434/v1/'
            )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.initial_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                n=1,
                temperature=0.5,
                stop=None
            )

            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise e 
            
    def _get_response_from_gemini(self, user_message):        
        model = genai.GenerativeModel('gemini-pro')
        genai.configure(api_key=self.gemini_key)

        prompt = self.initial_prompt
        prompt += user_message
        
        response = model.generate_content(prompt)

        # Extract the response text
        return response.text
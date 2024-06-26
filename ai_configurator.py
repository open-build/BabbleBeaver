import os
# import openai
from openai import OpenAI

import pathlib
import textwrap

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

class AIConfigurator:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.initial_prompt_file = os.getenv('INITIAL_PROMPT_FILE_PATH')
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
    
    def load_initial_prompt(self) -> str:
        """
        Fetches the contents of the file containing the context to be fed into the model and returns it as a string.
        """
        try:
            with open(self.initial_prompt_file, "r") as prompt_file:
                return prompt_file.read()
        except FileNotFoundError:
            return ""

    def _get_response_from_openai(self, user_message):
        # openai.api_key = self.openai_key
        # prompt = f"""
        # The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
        # {user_message}
        # """

        # response = openai.Completion.create(
        #     engine="davinci",  # Assuming using Davinci model here
        #     prompt=prompt,
        #     max_tokens=300,
        #     n=1,
        #     stop=None,
        #     temperature=0.5
        # )
        # return response.choices[0].text.strip()

        client = OpenAI(api_key=self.openai_key)
        initial_prompt = self.load_initial_prompt()

        response = client.chat.completions.create(
            messages = [{"role": "system", "content": initial_prompt}, {"role": "user", "content": user_message}],
            model= "gpt-3.5-turbo",
            max_tokens=300,
            n=1,
            temperature=0.5,
            stop=None
        )

        return response.choices[0].text
    
            
    def _get_response_from_gemini(self, user_message):

        GOOGLE_API_KEY = self.gemini_key
        
        model = genai.GenerativeModel('gemini-pro')
        genai.configure(api_key=GOOGLE_API_KEY)

        prompt = self.load_initial_prompt()
        prompt += user_message
        
        response = model.generate_content(prompt)

        # Extract the response text
        return response.text
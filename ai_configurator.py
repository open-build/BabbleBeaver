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
        self.active_provider = None

    def set_provider(self, provider_name):
        """Set the active AI provider based on user input."""
        if provider_name.lower() == 'ollama':
            self.active_provider = 'ollama'
            self.openai_key = 'DOES NOT MATTER'
        elif provider_name.lower() == 'openai' and self.openai_key:
            self.active_provider = 'openai'
        elif provider_name.lower() == 'gemini' and self.gemini_key:
            self.active_provider = 'gemini'
        else:
            raise ValueError(f"Unsupported AI provider or missing API key: {provider_name}")
    
    async def load_initial_prompt(self) -> str:
        """
        Fetches the contents of the file containing the context to be fed into the model and returns it as a string.
        """
        # handle the HTTP request asynchronously because requests.get() doesn't support it
        async with httpx.AsyncClient() as client:
            try:
                initial_prompt_request = await client.get("http://0.0.0.0:8000/pre_user_prompt")
                data = initial_prompt_request.json()
                return data["context"]
            except httpx.RequestError:
                return ""

    # async def get_response(self, user_message):
    #     initial_prompt = await self.load_initial_prompt()
    #     if self.active_provider == 'openai':
    #         return self._get_response_from_openai(initial_prompt, user_message)
    #     elif self.active_provider == 'gemini':
    #         return self._get_response_from_gemini(user_message)
    #     else:
    #         raise ValueError("No AI service configured.")

    def get_response(self, user_message):
        if self.active_provider in {'openai', 'ollama'}:
            return self._get_response_from_openai(user_message)
        elif self.active_provider == 'gemini':
            return self._get_response_from_gemini(user_message)
        else:
            raise ValueError("No AI service configured.")

    # def _get_response_from_openai(self, initial_prompt, user_message):
    #     client = OpenAI(api_key=self.openai_key)

    #     response = client.chat.completions.create(
    #         messages = [{"role": "system", "content": initial_prompt}, {"role": "user", "content": user_message}],
    #         model= "gpt-3.5-turbo",
    #         max_tokens=300,
    #         n=1,
    #         temperature=0.5,
    #         stop=None
    #     )

    #     return response.choices[0].text
    
    def _get_response_from_openai(self, user_message):

        # this is default openai data
        model = "gpt-3.5-turbo-0125"
        client = openai.Client(
            api_key=self.openai_key
        )

        initial_prompt = f"""
            The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
        """

        if self.active_provider.lower() == 'ollama':
            model = "llama3"   # config?
            client = openai.Client(
                api_key="whocares",
                base_url='http://localhost:11434/v1'
            )

            initial_prompt = f"""
                The following is a conversation with an AI assistant named Bobo. The assistant is helpful, creative, clever, 
                and very friendly. Bobo knows he's an AI, that is is running the "{model}" model on locally using Ollama.
                One of the benefits of running locally is there is no cost for using Gemini or OpenAI which is not free.
            """

        initial_prompt = textwrap.dedent(initial_prompt)
        print(client)

        print(initial_prompt)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": initial_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise e

    
            
    def _get_response_from_gemini(self, user_message):

        GOOGLE_API_KEY = self.gemini_key
        
        model = genai.GenerativeModel('gemini-pro')
        genai.configure(api_key=GOOGLE_API_KEY)

        prompt = user_message

        # prompt = initial_prompt
        # prompt += user_message
        
        response = model.generate_content(prompt)

        # Extract the response text
        return response.text
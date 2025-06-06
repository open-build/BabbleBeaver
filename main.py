
# main.py
from http.client import HTTPException
import os
import logging
import importlib.util
from random import sample
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

import openai  # Corrected import
import tiktoken

from ai_configurator import AIConfigurator
from message_logger import MessageLogger


from google.cloud import aiplatform
import vertexai
from vertexai.preview.generative_models import  GenerativeModel
from google.cloud import aiplatform

# from openai import OpenAI
import tiktoken

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


# Initialize dependencies
ai_configurator = AIConfigurator()
message_logger = MessageLogger()

# Load prompt suggestions
try:
    with open("suggested-prompts.txt", "r") as new_file:
        prompt_list = new_file.readlines()
except FileNotFoundError:
    prompt_list = []

# Google Vertex AI Authentication, uvicorn main:app --reload      
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")
vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel('gemini-2.0-flash-lite-001')
aiplatform.init(
    project=PROJECT_ID,
    location=LOCATION
)

# FastAPI app instance

app = FastAPI(debug=True)

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_DOMAINS", "*").split(","),  # Ensure default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and template mounting
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def call_function_from_file(folder_path, module_name, function_name):
    """Safely loads a module and executes a function."""
    module_path = os.path.join(folder_path, f"{module_name}.py")

    if not os.path.exists(module_path):
        return "Module file does not exist."

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    func = getattr(module, function_name, None)
    if func is None:
        return "Function not found."

    return func()


@app.get("/pre_user_prompt", response_class=JSONResponse)
async def pre_user_prompt():
    """Fetch suggested prompts."""
    suggested_prompts = sample(prompt_list, min(3, len(prompt_list)))  # Fix for <3 prompts
    return JSONResponse(suggested_prompts)


@app.get("/post_response", response_class=JSONResponse)
async def post_response(keyword: str):
    """Fetch related news articles."""
    search_rss_feed = call_function_from_file("modules/buildly-collect", "news-blogs", "search_rss_feed")

    if callable(search_rss_feed):
        news = search_rss_feed(rss_url="https://www.buildly.io/news/feed/", keyword=keyword)
        return JSONResponse(news)
    
    return JSONResponse({"error": "Failed to fetch news"}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    """Render chat UI."""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/chatbot")
async def chatbot(request: Request):
    
    data = await request.json()
    user_message, history, tokens = data.get("prompt"), data.get("history"), data.get("tokens")

    llm = "gemini-2.0-flash" # specify the model you want to use
    provider = "gemini" # specify the provider for this model
    tokenizer = tiktoken.get_encoding("cl100k_base") # specify the tokenizer to use for this model
    tokenizer_function = lambda text: len(tokenizer.encode(text)) # specify the tokenizing function to use
    with open("initial-prompt.txt", "r") as prompt_file:
        initial_prompt = prompt_file.read().strip()

    # specify the completion function you'd like to use
    def completion_function(api_key: str, 
                   initial_prompt: Optional[str],
                   user_message: str, 
                   conversation_history: str, 
                   max_tokens: int, 
                   temperature: float,
                   model_name: str):
        
        '''
        Genimi Model from Vertex AI
        '''
        full_prompt = f"""You are a helpful assistant that provides resaurant names and menu items to questions for users in Seattle. 
        Answer the following user question using ONLY the relevant restaurant and product details provided below. Be specific, concise, and friendly. 
        User Question:
        {user_message}
        """

        # if provider == "openai":
        #     client = OpenAI(api_key=api_key)

        #     try:
        #         response = client.chat.completions.create(
        #             model=model_name,
        #             messages=[
        #                 {"role": "system", "content": initial_prompt},
        #                 {"role": "user", "content": conversation_history + user_message}
        #             ],
        #             max_tokens=max_tokens,
        #             temperature=temperature,
        #         )

        #         return response.choices[0].message.content.strip()
            
        #     except Exception as e:
        #         raise e
        # else:

        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(model_name=ENDPOINT_ID)
        response = model.generate_content(user_message)
        return response.candidates[0].content.parts[0].text
        #     import google.generativeai as genai

        #     model = genai.GenerativeModel(model_name)
        #     genai.configure(api_key=api_key)
        #     prompt = user_message
            
        #     response = model.generate_content(prompt)

        #     # Extract the response text
        #     return response.text
        
    message_logger.log_message(user_message)

    try:
        ai_configurator.set_model(provider, llm, tokenizer_function, completion_function, use_initial_prompt=True)
        chat_response = await ai_configurator.process_response(history, user_message, tokens)  # Fixed call
        return chat_response
    except Exception as e:
        logger.error(f"Error in chatbot processing: {e}")
        return JSONResponse({"response": "Sorry... An error occurred."}, status_code=500)

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
from ai_configurator import AIConfigurator
from message_logger import MessageLogger
from response_logger import ChatLogger

from google.cloud import aiplatform
import vertexai
from vertexai.preview.generative_models import  GenerativeModel
from google.cloud import aiplatform
from google import genai
from google.genai import types

# DB
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json
import databases

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


# Initialize dependencies
ai_configurator = AIConfigurator()
message_logger = MessageLogger()
response_logger = ChatLogger()

# Load prompt suggestions
try:
    with open("suggested-prompts.txt", "r") as new_file:
        prompt_list = new_file.readlines()
except FileNotFoundError:
    prompt_list = []

# Google Vertex AI Authentication, uvicorn main:app --reload      
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.getenv("PROJECT_ID")
PROJECT_NAME = os.getenv("PROJECT_NAME")
LOCATION = os.getenv("LOCATION")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")


# DATABASE_URL = "postgresql://user:password@localhost/dbname"
# database = databases.Database(DATABASE_URL)
# DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost:5432/myfastapidb"
# model_config = SettingsConfigDict(env_file=".env", extra="ignore")

vertexai.init(project=PROJECT_NAME, location=LOCATION)
model = GenerativeModel(os.getenv("FINE_TUNED_MODEL"))
aiplatform.init(
    project=PROJECT_ID,
    location=LOCATION
)

# FastAPI app instance
app = FastAPI(debug=True)

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_DOMAINS", "*").split(","),
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


@app.post("/pre_user_prompt", response_class=JSONResponse)
async def pre_user_prompt(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    """Fetch suggested prompts."""
    suggested_prompts = sample(prompt_list, min(4, len(prompt_list)))
    prompt_history = response_logger.select_all_messages(session_id)
    # print(prompt_history)
    return {"suggested_prompts": suggested_prompts, 
            "prompt_history": prompt_history
        }


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
    return templates.TemplateResponse("chat.html", {"request": request})


'''
Generate answer with genai(kai_fine_2_5_v2) client from Vertex AI
return dict
'''
def generate_from(user_prompt, project_id, location, endpoint_id):
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    model=endpoint_id
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_prompt)
            ]
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature = 1,
        top_p = 1,
        seed = 0,
        max_output_tokens = 65535,
        safety_settings = [types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
        )],
        thinking_config=types.ThinkingConfig(
        thinking_budget=-1,
        ),
    )

    full_text = ""
    model_version = None
    total_token_count = None

    for chunk in client.models.generate_content_stream(
        model = model,
        contents = contents,
        config = generate_content_config,
        ):
        try:
            parts = chunk.candidates[0].content.parts
            for part in parts:
                if hasattr(part, "text"):
                    full_text += part.text

            if model_version is None and hasattr(chunk, "model_version"):
                model_version = chunk.model_version

            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                usage = chunk.usage_metadata
                if hasattr(usage, "total_token_count") and usage.total_token_count:
                    total_token_count = usage.total_token_count

        except Exception as e:
            print("Error while parsing chunk:", e)

    parsed_output = {
        "text": full_text.strip(),
        "model_version": model_version,
        "total_token_count": total_token_count
    }
    return parsed_output


@app.post("/chatbot")
async def chatbot(request: Request):
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    endpoint_id = os.getenv("ENDPOINT_ID")
    
    data = await request.json()
    user_message, history, tokens, session_id = data.get("prompt"), data.get("history"), data.get("tokens") , '12344412'       

    full_prompt = f"""You are a helpful assistant that provides resaurant names and menu items to questions for users in Seattle. 
        Answer the following user question using ONLY the relevant restaurant and product details provided below. Be specific, concise, and friendly. 
        User Question:
        {user_message}
        """
    
    # Record bot response
    response_logger.insert_message(session_id, "user", user_message)

    response = generate_from(full_prompt, project_id, location, endpoint_id)
    response_dict = response

    message_logger.log_message(user_message, session_id)
    
    response_logger.insert_message(session_id, "bot", response_dict['text'])

    return {'prompt': full_prompt, 'user_prompt': user_message, 'kai_response': response_dict['text'], 'model_version': response_dict['model_version'], 'history': "response_logger.select_all_messages(session_id)", 'tokens': response_dict['total_token_count']}



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
from google import genai
from google.genai import types

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
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.getenv("PROJECT_ID")
PROJECT_NAME = os.getenv("PROJECT_NAME")
LOCATION = os.getenv("LOCATION")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")

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


'''
Generate answer with genai(kai_fine_2_5_v2) client from Vertex AI
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
            # Get text part(s) from the candidate
            parts = chunk.candidates[0].content.parts
            for part in parts:
                if hasattr(part, "text"):
                    full_text += part.text

            # Get model_version once
            if model_version is None and hasattr(chunk, "model_version"):
                model_version = chunk.model_version

            # Get token count if it's in usage_metadata
            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                usage = chunk.usage_metadata
                if hasattr(usage, "total_token_count") and usage.total_token_count:
                    total_token_count = usage.total_token_count

        except Exception as e:
            print("Error while parsing chunk:", e)

    # Final parsed dictionary
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
    user_message, history, tokens = data.get("prompt"), data.get("history"), data.get("tokens")

    llm = "gemini-2.5-flash" # specify the model you want to use
    provider = "gemini" # specify the provider for this model
    tokenizer = tiktoken.get_encoding("cl100k_base") # specify the tokenizer to use for this model
    tokenizer_function = lambda text: len(tokenizer.encode(text)) # specify the tokenizing function to use
    # with open("initial-prompt.txt", "r") as prompt_file:
    #     initial_prompt = prompt_file.read().strip()

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


        response = generate_from(full_prompt, project_id, location, endpoint_id)
        print(response)
        print(history)
        return response

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

        # aiplatform.init(project=PROJECT_ID, location=LOCATION)
        # model = GenerativeModel(model_name=ENDPOINT_ID)
        # response = model.generate_content(user_message)
        # return response.candidates[0].content.parts[0].text
    
        #     import google.generativeai as genai

        #     model = genai.GenerativeModel(model_name)
        #     genai.configure(api_key=api_key)
        #     prompt = user_message
            
        #     response = model.generate_content(prompt)

        #     # Extract the response text
        #     return response.text
        

    full_prompt = f"""You are a helpful assistant that provides resaurant names and menu items to questions for users in Seattle. 
        Answer the following user question using ONLY the relevant restaurant and product details provided below. Be specific, concise, and friendly. 
        User Question:
        {user_message}
        """

    response = generate_from(full_prompt, project_id, location, endpoint_id)
    # message_logger.log_message(user_message)

    return {'prompt': full_prompt, 'kai_response': response, 'history': 'response', 'tokens': 'localNumTokens'}

    try:
        # chat_response = completion_function(user_message=user_message)
        ai_configurator.set_model(provider, llm, tokenizer_function, completion_function, use_initial_prompt=True)
        chat_response = ai_configurator.process_response(history, user_message, tokens)  # Fixed call
        # print("chat_response:", chat_response)
        return chat_response
    except Exception as e:
        logger.error(f"Error in chatbot processing: {e}")
        return JSONResponse({"response": "Sorry... An error occurred."}, status_code=500)

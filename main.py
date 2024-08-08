# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from ai_configurator import AIConfigurator
from message_logger import MessageLogger

from openai import OpenAI
import tiktoken

import os
from random import sample
from typing import Optional

app = FastAPI(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)

ai_configurator = AIConfigurator()
message_logger = MessageLogger()
with open("suggested-prompts.txt", "r") as new_file:
    prompt_list = new_file.readlines()

def call_function_from_file(folder_path, module_name, function_name):
    """
    Use to load a module and call the function from a file in a specific folder.
    
    Example usage:
    folder_path = "/path/to/your/folder"  # Update this path as needed
    module_name = "module"
    function_name = "example_function"

    Call the function
    result = call_function_from_file(folder_path, module_name, function_name)
    print(result)
    """
    # Check if the folder exists
    if os.path.exists(folder_path):
        # Add the folder path to the system path to allow importing
        import sys
        sys.path.append(folder_path)
        
        # Import the module
        module = __import__(module_name)
        
        # Get the function by name and call it
        func = getattr(module, function_name)
        return func()
    else:
        return "Folder does not exist."

@app.get("/pre_user_prompt", response_class=JSONResponse)
async def pre_user_prompt():
    """
    Simulate fetching data from a third-party API before the user sends a prompt.
    This data could be used to give context or information to the user.
    """
    suggested_prompts = sample(prompt_list, 3)
    return JSONResponse(suggested_prompts)

@app.get("/post_response", response_class=JSONResponse)
async def post_response(keyword: str):
    """
    Fetching additional data from a third-party API or feed after sending a response to the user.
    This could be further reading, sources, or related topics.
    """
    search_rss_feed = call_function_from_file("modules/buildly-collect", "news-blogs", "search_rss_feed")
    # Get Data from Buildly News Blogs
    # Search the feed
    news = search_rss_feed(rss_url = "https://www.buildly.io/news/feed/", keyword = keyword)
    
    return JSONResponse(news)

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    # return JSONResponse({"status": "Server is runnning on port 8000"})
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/chatbot")
async def chatbot(request: Request):
    data = await request.json()
    user_message, history, tokens = data.get("prompt"), data.get("history"), data.get("tokens")

    llm = "gpt-3.5-turbo" # specify the model you want to use
    provider = "openai" # specify the provider for this model
    tokenizer = tiktoken.get_encoding("cl100k_base") # specify the tokenizer to use for this model
    tokenizer_function = lambda text: len(tokenizer.encode(text)) # specify the tokenizing function to use

    # specify the completion function you'd like to use
    def completion_function(api_key: str, 
                   initial_prompt: Optional[str],
                   user_message: str, 
                   conversation_history: str, 
                   max_tokens: int, 
                   temperature: float,
                   model_name: str):
        
        client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": initial_prompt},
                    {"role": "user", "content": conversation_history + user_message}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise e

    message_logger.log_message(user_message)
    
    try:
        ai_configurator.set_model(provider, llm, tokenizer_function, completion_function, use_initial_prompt=True)
        chat_response = ai_configurator.get_response(history, user_message, tokens)
        return chat_response
    except Exception as e:
        print(f"An error occurred: {e}")
        return JSONResponse({"response": "Sorry... An error occurred."})
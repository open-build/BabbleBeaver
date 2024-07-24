# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from ai_configurator import AIConfigurator
from message_logger import MessageLogger

import os
from random import sample

app = FastAPI(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/chatbot")
async def chatbot(request: Request):
    data = await request.json()
    user_message, history, tokens = data.get("prompt"), data.get("history"), data.get("tokens")
    ai_provider = "ollama"  # Default AI provider

    message_logger.log_message(user_message)
    
    try:
        ai_configurator.set_provider(ai_provider)  # Set the AI provider based on user input
        chat_response = ai_configurator.get_response(history, user_message, tokens)
        return chat_response
    except Exception as e:
        print(f"An error occurred: {e}")
        return JSONResponse({"response": "Sorry... An error occurred."})
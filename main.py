# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from ai_configurator import AIConfigurator
from message_logger import MessageLogger

app = FastAPI(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ai_configurator = AIConfigurator()
message_logger = MessageLogger()

@app.get("/pre_user_prompt", response_class=JSONResponse)
async def pre_user_prompt():
    """
    Simulate fetching data from a third-party API before the user sends a prompt.
    This data could be used to give context or information to the user.
    """
    # Example of what data might look like
    data = {
        "text": "Here's something interesting to get us started:",
        "link": "https://example.com/interesting-article",
        "description": "An intriguing article on the impact of AI in modern society."
    }
    return JSONResponse(data)

@app.get("/post_response", response_class=JSONResponse)
async def post_response():
    """
    Simulate fetching additional data from a third-party API after sending a response to the user.
    This could be further reading, sources, or related topics.
    """
    # Example of additional data to send back
    additional_data = {
        "text": "If you found that interesting, you might also enjoy:",
        "link": "https://example.com/follow-up-article",
        "description": "A follow-up piece on the future of AI applications."
    }
    return JSONResponse(additional_data)

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/chatbot")
async def chatbot(request: Request):
    data = await request.json()
    user_message = data.get("prompt")
    ai_provider = "gemini"  # Default AI provider

    message_logger.log_message(user_message)
    
    try:
        ai_configurator.set_provider(ai_provider)  # Set the AI provider based on user input
        chat_response = ai_configurator.get_response(user_message)
        return JSONResponse({"response": chat_response})
    except Exception as e:
        print(f"An error occurred: {e}")
        return JSONResponse({"response": "Sorry... An error occurred."})

import os
import logging
import importlib.util
from random import sample
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import tiktoken
import time
import asyncio

from ai_configurator import AIConfigurator
from message_logger import MessageLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_DOMAINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ai_configurator = AIConfigurator()
message_logger = MessageLogger()

try:
    with open("suggested-prompts.txt", "r") as new_file:
        prompt_list = new_file.readlines()
except FileNotFoundError:
    prompt_list = []

UPLOAD_DIR = "secure_credentials"
os.makedirs(UPLOAD_DIR, exist_ok=True)
CREDENTIALS_PATH = os.path.abspath(os.path.join(UPLOAD_DIR, "service_account.json"))

def ensure_google_credentials_env():
    """Set the GOOGLE_APPLICATION_CREDENTIALS env var if the file exists."""
    if os.path.exists(CREDENTIALS_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
        logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS to {CREDENTIALS_PATH}")

def credentials_needed(provider: str):
    if provider.lower() in ["gemini", "vertex", "vertexai"]:
        logger.info(f"Checking for credentials file at: {CREDENTIALS_PATH}")
        return not os.path.exists(CREDENTIALS_PATH)
    return False

@app.get("/upload_credentials", response_class=HTMLResponse)
async def upload_credentials_form(request: Request):
    html_content = """
    <html>
        <body>
            <h2>Upload Google Service Account Credentials</h2>
            <form action="/upload_credentials" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept=".json">
                <input type="submit">
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/upload_credentials")
async def upload_credentials(file: UploadFile = File(...)):
    if not file.filename.endswith(".json"):
        logger.error("Attempted to upload non-JSON credentials file.")
        return JSONResponse({"error": "Only JSON files are allowed."}, status_code=400)
    save_path = CREDENTIALS_PATH
    with open(save_path, "wb") as buffer:
        buffer.write(await file.read())
    ensure_google_credentials_env()
    logger.info(f"Credentials uploaded and saved to {save_path}")
    return RedirectResponse(url="/", status_code=303)

def call_function_from_file(folder_path, module_name, function_name):
    module_path = os.path.join(folder_path, f"{module_name}.py")
    if not os.path.exists(module_path):
        logger.error(f"Module file {module_path} does not exist.")
        return None
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module, function_name, None)
    if func is None:
        logger.error(f"Function {function_name} not found in {module_name}.py")
    return func

@app.get("/pre_user_prompt", response_class=JSONResponse)
async def pre_user_prompt():
    suggested_prompts = sample(prompt_list, min(3, len(prompt_list))) if prompt_list else []
    logger.info(f"Serving {len(suggested_prompts)} suggested prompts.")
    return JSONResponse(suggested_prompts)

@app.get("/post_response", response_class=JSONResponse)
async def post_response(keyword: str):
    search_rss_feed = call_function_from_file("modules/buildly-collect", "news-blogs", "search_rss_feed")
    if callable(search_rss_feed):
        news = search_rss_feed(rss_url="https://www.buildly.io/news/feed/", keyword=keyword)
        logger.info(f"Fetched news for keyword: {keyword}")
        return JSONResponse(news)
    logger.error("Failed to fetch news.")
    return JSONResponse({"error": "Failed to fetch news"}, status_code=500)

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    provider = os.getenv("PROVIDER", "gemini")
    creds_missing = credentials_needed(provider)
    upload_html = ""
    if creds_missing:
        upload_html = '<div style="color:red;">Google credentials missing. <a href="/upload_credentials">Upload here</a></div>'
        logger.warning("Google credentials missing, prompting user to upload.")
    else:
        ensure_google_credentials_env()
    return templates.TemplateResponse("chat.html", {"request": request, "upload_html": upload_html})

@app.post("/chatbot")
async def chatbot(request: Request):
    start_time = time.time()
    data = await request.json()
    user_message = data.get("prompt")
    history = data.get("history")
    tokens = data.get("tokens")

    # Log incoming request data
    logger.info(f"Received /chatbot POST: prompt={user_message}, tokens={tokens}, history keys={list(history.keys()) if isinstance(history, dict) else type(history)}")

    # Validation
    if user_message is None or history is None or tokens is None:
        logger.error(f"Missing required fields: prompt={user_message}, history={history}, tokens={tokens}")
        return JSONResponse({"response": "Missing required fields in request."}, status_code=400)

    provider = os.getenv("PROVIDER", "gemini").lower()
    llm = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokenizer_function = lambda text: len(tokenizer.encode(text))
    with open("initial-prompt.txt", "r") as prompt_file:
        initial_prompt = prompt_file.read().strip()

    # Select completion function based on provider
    if provider in ["gemini", "vertex", "vertexai"]:
        logger.info("Using Gemini/Vertex AI provider.")
        from google.cloud import aiplatform
        import vertexai
        from vertexai.preview.generative_models import GenerativeModel

        # Initialize model ONCE at startup (global) for performance
        global gemini_model
        if "gemini_model" not in globals():
            logger.info("Initializing Gemini model at startup.")
            try:
                aiplatform.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION"))
                gemini_model = GenerativeModel(model_name=os.getenv("ENDPOINT_ID", llm))
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                return JSONResponse({"response": f"Failed to initialize Gemini model: {e}"}, status_code=500)

        def gemini_completion_function(api_key: str, initial_prompt: Optional[str], user_message: str, conversation_history: str, max_tokens: int, temperature: float, model_name: str):
            logger.info("Calling Gemini model for completion.")
            try:
                response = gemini_model.generate_content(user_message)
                logger.info("Gemini model response received.")
                return response.candidates[0].content.parts[0].text
            except Exception as e:
                logger.error(f"Gemini model call failed: {e}")
                return f"Error from Gemini: {e}"

        completion_function = gemini_completion_function
        if credentials_needed(provider):
            logger.error("Google Vertex AI credentials missing.")
            return JSONResponse({"response": "Google Vertex AI credentials missing. Please upload them."}, status_code=400)

    elif provider == "openai":
        logger.info("Using OpenAI provider.")
        import openai

        def openai_completion_function(api_key: str, initial_prompt: Optional[str], user_message: str, conversation_history: str, max_tokens: int, temperature: float, model_name: str):
            openai.api_key = api_key
            try:
                logger.info("Calling OpenAI ChatCompletion.")
                response = openai.ChatCompletion.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": initial_prompt},
                        {"role": "user", "content": conversation_history + user_message}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                logger.info("OpenAI response received.")
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI call failed: {e}")
                return f"Error from OpenAI: {e}"

        completion_function = openai_completion_function

    else:
        logger.error(f"Unknown provider: {provider}")
        return JSONResponse({"response": f"Unknown provider: {provider}"}, status_code=400)

    message_logger.log_message(user_message)

    try:
        logger.info("Setting model in AIConfigurator.")
        ai_configurator.set_model(provider, llm, tokenizer_function, completion_function, use_initial_prompt=True)

        # Use run_in_executor to avoid blocking event loop for sync code
        loop = asyncio.get_event_loop()
        logger.info("Calling process_response in executor.")
        chat_response = await loop.run_in_executor(
            None, ai_configurator.process_response, history, user_message, tokens
        )
        logger.info(f"process_response returned: {chat_response}")

        elapsed = time.time() - start_time
        logger.info(f"/chatbot request processed in {elapsed:.2f} seconds.")

        if isinstance(chat_response, dict) and "response" in chat_response:
            # Flatten the response for the frontend
            return JSONResponse({
                "response": chat_response["response"],
                "usedTokens": chat_response.get("usedTokens"),
                "updatedHistory": chat_response.get("updatedHistory")
            })
        else:
            return JSONResponse({"response": chat_response})
    except Exception as e:
        import traceback
        logger.error(f"Error in chatbot processing: {e}\n{traceback.format_exc()}")
        return JSONResponse({"response": f"Sorry... An error occurred: {e}"}, status_code=500)

@app.get("/health")
async def health_check():
    try:
        ai_configurator.get_response("health check")
        logger.info("Health check passed.")
        return JSONResponse({"status": "healthy"})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=500)
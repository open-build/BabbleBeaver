# main.py
from fastapi import HTTPException
import os
import logging
import importlib.util
from random import sample
from typing import Optional
import sys

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import openai
from ai_configurator import AIConfigurator
from message_logger import MessageLogger
from response_logger import ChatLogger
from user_context import fetch_user_context, format_user_context, resolve_identity
from daily_scores import upsert_daily_scores

from google.cloud import aiplatform, bigquery
import vertexai
from vertexai.preview.generative_models import GenerativeModel

from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_configurator = AIConfigurator()
message_logger = MessageLogger()
response_logger = ChatLogger()

# Load prompt suggestions
try:
    with open("suggested-prompts.txt", "r") as new_file:
        prompt_list = new_file.readlines()
except FileNotFoundError:
    prompt_list = []

PROJECT_ID = os.getenv("PROJECT_ID")
PROJECT_NAME = os.getenv("PROJECT_NAME")
LOCATION = os.getenv("LOCATION")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")

bq_client = bigquery.Client(project=PROJECT_ID)
vertexai.init(project=PROJECT_NAME, location=LOCATION)
model = GenerativeModel(os.getenv("FINE_TUNED_MODEL"))
aiplatform.init(
    project=PROJECT_ID,
    location=LOCATION
)

# FastAPI app instance
app = FastAPI(debug=True)

# Middleware for CORS
# Configure allowed origins from environment or use defaults
cors_origins = os.getenv("CORS_ALLOWED_DOMAINS", "").strip()

if cors_origins:
    # Use domains from .env if specified
    allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
else:
    # Default origins for local development and production
    allowed_origins = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        # Add your production domains here or in .env
        # "https://your-production-domain.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_DOMAINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static and template mounting
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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


def serialize_chat(chat):
    return {
        # "id": chat.id,
        "session_id": chat.session_id,
        "sender": chat.sender,
        "message": chat.message,
        "timestamp": chat.timestamp.isoformat() if chat.timestamp else None
    }


@app.post("/pre_user_prompt", response_class=JSONResponse)
async def pre_user_prompt(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    suggested_prompts = sample(prompt_list, min(4, len(prompt_list)))
    chat_records = response_logger.select_all_messages(session_id)
    prompt_history = [serialize_chat(chat) for chat in chat_records]
    return {
        "suggested_prompts": suggested_prompts,
        "prompt_history": prompt_history
    }


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
async def index_view(request: Request):
    """Render public index page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def test_view(request: Request):
    """Render test chat UI (authentication via frontend)."""
    # Frontend will handle auth by sending bearer token with API requests
    return templates.TemplateResponse("test.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat_view(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


'''
Vectorize messages with Cosine sim
'''
def vector_search_restaurants(query_text: str, top_k: int = 10) -> list:
    """Search for similar restaurants using BigQuery vector search"""
    
    sql = f"""
        SELECT DISTINCT
        base.restaurant,
        base.restaurant_id,
        base.dish,
        base.summary,
        base.tags,
        base.category,
        base.calories,
        base.protein,
        base.carbohydrates,
        distance
        FROM VECTOR_SEARCH(
        TABLE `208535887371.restaurant_data.seattle_data_with_embeddings`,
        'ml_generate_embedding_result',
        (
            SELECT ml_generate_embedding_result
            FROM ML.GENERATE_EMBEDDING(
            MODEL `208535887371.restaurant_data.embedding_model`,
            (SELECT @query_text AS content),
            STRUCT(TRUE AS flatten_json_output)
            )
        ),
        top_k => 30
        )
        LIMIT 10
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_text", "STRING", query_text),
            bigquery.ScalarQueryParameter("top_k", "INT64", top_k)
        ]
    )

    results = bq_client.query(sql, job_config=job_config).to_dataframe()
    return results.to_dict('records')


'''
Generate answer with genai(kai_fine_2_5_v2) client from Vertex AI
return dict
'''
def generate_from_v2(user_query: str, search_results: list, project_id, location, endpoint_id, user_context_block: str = "") -> str:
    """Optimized version - fewer tokens, better accuracy"""
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    top_results = search_results[:3]
    model=endpoint_id
    generate_content_config = types.GenerateContentConfig(
        temperature = 0.3,
        top_p = 0.35,
        seed = 0,
        max_output_tokens = 500,
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
            thinking_budget=256,
        ),
    )
    
    context = ""
    for idx, result in enumerate(top_results, 1):
        dish = result.get('dish', 'Unknown dish')
        restaurant = result.get('restaurant', 'Unknown restaurant')
        summary = result.get('summary', '')
        category = result.get('category', '')

        context += f"{idx}. {dish} - {restaurant}\n"
        context += f"   {summary}\n"
        if category:
            context += f"   Category: {category}\n"

        # Nutrition from flat columns
        parts = []
        if result.get('calories'):
            parts.append(f"{result['calories']} cal")
        if result.get('protein'):
            parts.append(f"{result['protein']} protein")
        if result.get('carbohydrates'):
            parts.append(f"{result['carbohydrates']} carbs")
        if parts:
            context += f"   Nutrition: {', '.join(parts)}\n"

    user_context_section = f"\n    {user_context_block}\n" if user_context_block else ""

    prompt = f"""
    You are Kai, DrunR's AI nutrition guide. Talk like a warm, encouraging friend
    who happens to know food and health well — natural and conversational, never
    clinical or robotic. Use "you," skip jargon, and don't restate the question.
{user_context_section}
    User request:
    {user_query}

    Available menu results:
    {context}

    FIRST decide which mode to use:

    INDECISION MODE — use this when the user sounds stuck, torn, or can't choose
    between options (e.g. "I can't decide," "which one?", "they all look good,"
    "help me pick," or they list a few items and ask you to choose). Instead of
    just handing them an answer, gently guide them to their own choice:
    - Open with one warm, reassuring sentence.
    - Ask 1-2 short Socratic questions that help them weigh the real menu options
      against what matters to them right now (e.g. "Are you after something light
      or something that'll keep you full?", "Do you want to lean into your protein
      goal today, or just something that sounds good?"). Anchor the questions to
      the actual menu results and their profile/health data when present.
    - Offer to narrow it down once they answer. Do NOT lecture or pick for them
      unless they ask you to. Keep it to a few sentences — skip the 3-part format.

    RECOMMENDATION MODE — use this for normal requests where the user wants a
    suggestion. Reply in exactly these three parts, with no headers shown to the
    user other than the bold labels below:

    1. A short, friendly opener (one sentence) and then 1-2 concrete picks — a
       meal and/or a restaurant from the menu results. Name the dish and the spot,
       and one quick reason each. Keep it to a couple of sentences, not a long list.

    2. **Why this fits you:** 1-2 short bullets that highlight the specific user
       profile detail(s) and recent health data you used (e.g. "your resting heart
       rate is steady at 48 bpm" or "you're pescatarian and avoiding dairy"). Only
       mention data that is actually present in the USER HEALTH PROFILE above.

    3. A single friendly closing line with one clear next step (a question or
       suggestion).

    Rules:
    - Use ONLY the available menu results for dish/restaurant facts. Never invent
      nutrition, ingredients, restaurant details, or health claims.
    - In INDECISION MODE, only reference dishes/restaurants that appear in the menu
      results above when framing your questions.
    - If the user profile or health data is empty, skip part 2 gracefully rather
      than guessing — just give the picks and the closing line.
    - Respect dietary preferences, allergies, and GLP-1 medication when present.
    - Favor GLP-1-friendly patterns when relevant: higher protein, moderate
      calories, lower added sugar, lighter/non-fried options.
    - Keep the whole reply tight and human — a few sentences, not an essay.
    - Be supportive, never preachy. Do not give medical advice.
    """

    chunk = client.models.generate_content(
        model = model,
        contents = prompt,
        config = generate_content_config
    )
    
    text = chunk.candidates[0].content.parts[0].text

    # if model_version is None and hasattr(chunk, "model_version"):
    #     model_version = chunk.model_version

    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
        usage = chunk.usage_metadata
        if hasattr(usage, "total_token_count") and usage.total_token_count:
            total_token_count = usage.total_token_count

    parsed_output = {
        "text": text.strip(),
        "model_version": 1.5,
        "total_token_count": total_token_count
    }
    
    return parsed_output


@app.post("/chatbot")
async def chatbot(request: Request):
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    endpoint_id = os.getenv("ENDPOINT_ID")
    
    data = await request.json()
    user_message, history, tokens, session_id = data.get("prompt"), data.get("history"), data.get("tokens") , data.get("session_id", '12344412')

    # Identity comes from the signed bearer token, never the request body, so a
    # caller cannot pull another user's health data by guessing a core_user_uuid.
    core_user_uuid, bearer_token = resolve_identity(request.headers.get("Authorization"))

    # User health profile + wearable biometrics from user_service (optional)
    user_context_block = ""
    if core_user_uuid:
        user_ctx = await fetch_user_context(core_user_uuid, bearer_token=bearer_token)
        user_context_block = format_user_context(user_ctx)
        # Deterministic MAI scores (SCORING.md): persist today's snapshot and
        # inject the block to weight recommendations.
        score_block = upsert_daily_scores(user_ctx, core_user_uuid)
        if score_block:
            user_context_block = (
                f"{user_context_block}\n\n{score_block}" if user_context_block else score_block
            )

    # Similarity Search from BigQuery vectorDB
    search_results = vector_search_restaurants(
            query_text=user_message,
            top_k=20
        )

    full_prompt = f"""You are a helpful assistant that provides resaurant names and menu items to questions for users in Seattle. 
        Answer the following user question using ONLY the relevant restaurant and product details provided below. Be specific, concise, and friendly. 
        User Question:
        {user_message}
        """
    
    # print(user_message)

    response_logger.insert_message(session_id, "user", user_message)

    # response = generate_from(full_prompt, project_id, location, endpoint_id)
    response = generate_from_v2(user_message, search_results, project_id, location, endpoint_id, user_context_block)
    response_dict = response

    message_logger.log_message(user_message, session_id)
    
    response_logger.insert_message(session_id, "bot", response_dict['text'])

    return {'prompt': full_prompt, 'user_prompt': user_message, 'kai_response': response_dict['text'], 'model_version': response_dict['model_version'], 'history': "response_logger.select_all_messages(session_id)", 'tokens': response_dict['total_token_count']}

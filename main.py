# main.py
from http.client import HTTPException
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

import openai  # Corrected import
from ai_configurator import AIConfigurator
from message_logger import MessageLogger
from response_logger import ChatLogger

import google.generativeai as genai
from google.cloud import aiplatform
import vertexai
from vertexai.preview.generative_models import  GenerativeModel
from google.cloud import aiplatform

import google.generativeai as genai
from google.generativeai import types

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

# Protected static file serving with token authentication
async def verify_static_access(request: Request):
    """Verify token for static file access."""
    # Check for token in query parameter or Authorization header
    token = request.query_params.get("token")
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return Response(content="Unauthorized: Token required", status_code=401)
    
    try:
        from auth import verify_token
        verify_token(token)
    except Exception as e:
        return Response(content=f"Unauthorized: {str(e)}", status_code=401)


# Mount static files with custom middleware for authentication
# This requires users to be authenticated to access the frontend
class AuthStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        # Only check auth for HTML files (allow CSS/JS to be accessed if HTML is accessed)
        request = Request(scope, receive)
        path = request.url.path
        
        # For now, we'll protect all static access
        # In production, you might want more granular control
        if not path.endswith(('.css', '.js', '.png', '.jpg', '.ico')):
            auth_result = await verify_static_access(request)
            if isinstance(auth_result, Response):
                await auth_result(scope, receive, send)
                return
        
        await super().__call__(scope, receive, send)


app.mount("/static", AuthStaticFiles(directory="static"), name="static")


# =============================================================================
# ADMIN AUTHENTICATION ENDPOINTS
# =============================================================================

@app.post("/admin/login")
async def admin_login(request: Request):
    """Admin login endpoint - returns JWT token."""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return JSONResponse(
                {"error": "Username and password required"},
                status_code=400
            )
        
        if not verify_admin_credentials(username, password):
            return JSONResponse(
                {"error": "Invalid credentials"},
                status_code=401
            )
        
        # Return the API key from environment
        api_key = os.getenv("API_KEY")
        if not api_key:
            return JSONResponse(
                {"error": "API_KEY not configured on server"},
                status_code=500
            )
        
        return JSONResponse({
            "access_token": api_key,
            "token_type": "bearer",
            "message": "Login successful"
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return JSONResponse(
            {"error": "Login failed"},
            status_code=500
        )


@app.post("/admin/generate-api-token")
async def generate_new_api_token(
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """
    Generate a new API token and save to database.
    Token works immediately without server restart.
    
    Request body:
        description: Token description (optional, default: "API Access Token")
        expires_days: Days until expiration (optional, default: 365, null = never expires)
    """
    try:
        data = await request.json()
        description = data.get("description", "API Access Token")
        expires_days = data.get("expires_days", 365)
        
        # Create token and save to database
        result = token_manager.create_token(
            description=description,
            expires_days=expires_days
        )
        
        return JSONResponse({
            "token": result["token"],  # Plain token - show ONCE
            "id": result["id"],
            "description": result["description"],
            "created_at": result["created_at"],
            "expires_at": result["expires_at"],
            "message": "Token created successfully. Save this token - it will not be shown again!",
            "works_immediately": True
        })
        
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return JSONResponse(
            {"error": "Failed to generate token"},
            status_code=500
        )


@app.get("/admin/tokens")
async def list_api_tokens(current_user: dict = Depends(require_admin)):
    """
    List all API tokens (excluding token values).
    Shows active, expired, and revoked tokens.
    """
    try:
        tokens = token_manager.list_tokens()
        
        # Add environment token info
        env_token = os.getenv("API_KEY")
        env_token_info = None
        if env_token:
            env_token_info = {
                "source": "environment",
                "description": "Environment Variable Token (API_KEY)",
                "is_active": True,
                "is_expired": False,
                "created_at": None,
                "expires_at": None,
                "last_used_at": None,
                "token_preview": env_token[:8] + "..." + env_token[-4:]
            }
        
        return JSONResponse({
            "tokens": tokens,
            "env_token": env_token_info
        })
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        return JSONResponse(
            {"error": "Failed to list tokens"},
            status_code=500
        )


@app.post("/admin/tokens/{token_id}/revoke")
async def revoke_api_token(
    token_id: int,
    current_user: dict = Depends(require_admin)
):
    """
    Revoke an API token by ID.
    Revoked tokens will immediately stop working.
    """
    try:
        success = token_manager.revoke_token(token_id)
        
        if success:
            return JSONResponse({
                "message": f"Token {token_id} revoked successfully"
            })
        else:
            return JSONResponse(
                {"error": "Token not found"},
                status_code=404
            )
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        return JSONResponse(
            {"error": "Failed to revoke token"},
            status_code=500
        )


# =============================================================================
# ADMIN LOG MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/admin/logs")
async def get_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Retrieve chat logs with filtering options."""
    try:
        logs = message_logger.retrieve_messages(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            provider=provider
        )
        
        total_count = message_logger.get_message_count(
            start_date=start_date,
            end_date=end_date,
            provider=provider
        )
        
        return JSONResponse({
            "logs": logs,
            "total": total_count,
            "limit": limit,
            "offset": offset
        })
        
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        return JSONResponse(
            {"error": "Failed to retrieve logs"},
            status_code=500
        )


@app.get("/admin/logs/export")
async def export_logs(
    format: str = "jsonl",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Export logs in format suitable for fine-tuning."""
    try:
        export_data = message_logger.export_for_fine_tuning(
            format=format,
            start_date=start_date,
            end_date=end_date,
            provider=provider
        )
        
        media_type = "application/jsonl" if format == "jsonl" else "application/json"
        filename = f"training_data.{format}"
        
        return Response(
            content=export_data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        return JSONResponse(
            {"error": "Failed to export logs"},
            status_code=500
        )


@app.get("/admin/logs/analytics")
async def get_log_analytics(current_user: dict = Depends(require_admin)):
    """Get analytics about logged messages."""
    try:
        analytics = message_logger.get_analytics()
        return JSONResponse(analytics)
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return JSONResponse(
            {"error": "Failed to get analytics"},
            status_code=500
        )


# =============================================================================
# ADMIN LLM CONFIGURATION ENDPOINTS
# =============================================================================

@app.get("/admin/llm/providers")
async def list_llm_providers(current_user: dict = Depends(require_admin)):
    """List all configured LLM providers."""
    try:
        providers = llm_manager.list_providers()
        return JSONResponse({"providers": providers})
        
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        return JSONResponse(
            {"error": "Failed to list providers"},
            status_code=500
        )


@app.post("/admin/llm/providers/{provider}/update")
async def update_llm_provider(
    provider: str,
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """Update LLM provider configuration."""
    try:
        data = await request.json()
        
        # Validate provider
        try:
            provider_enum = LLMProvider(provider)
        except ValueError:
            return JSONResponse(
                {"error": f"Invalid provider: {provider}"},
                status_code=400
            )
        
        llm_manager.update_provider_config(
            provider=provider_enum,
            model_name=data.get("model_name"),
            api_key=data.get("api_key"),
            priority=data.get("priority"),
            enabled=data.get("enabled"),
            max_tokens=data.get("max_tokens"),
            temperature=data.get("temperature")
        )
        
        return JSONResponse({
            "message": f"Provider {provider} updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating provider: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.post("/admin/llm/test")
async def test_llm(
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """Test LLM connection and response."""
    try:
        data = await request.json()
        prompt = data.get("prompt", "Hello, this is a test.")
        provider = data.get("provider")
        
        provider_enum = LLMProvider(provider) if provider else None
        
        result = llm_manager.generate(
            prompt=prompt,
            preferred_provider=provider_enum
        )
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error testing LLM: {e}")
        return JSONResponse(
            {"error": str(e), "success": False},
            status_code=500
        )


# =============================================================================
# ADMIN UI ENDPOINTS
# =============================================================================

@app.get("/admin", response_class=HTMLResponse)
async def admin_view(request: Request):
    """Render admin dashboard."""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/admin/context/stats")
async def context_stats(current_user: dict = Depends(require_admin)):
    """Get context manager statistics."""
    return JSONResponse(context_manager.get_stats())


@app.get("/admin/system-prompt")
async def get_system_prompt(current_user: dict = Depends(require_admin)):
    """Get current system prompt from initial-prompt.txt."""
    try:
        with open("initial-prompt.txt", "r") as f:
            prompt = f.read()
        return JSONResponse({"prompt": prompt})
    except FileNotFoundError:
        return JSONResponse({"prompt": ""})
    except Exception as e:
        logger.error(f"Error reading system prompt: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/system-prompt")
async def update_system_prompt(
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """Update system prompt in initial-prompt.txt."""
    try:
        data = await request.json()
        new_prompt = data.get("prompt", "")
        
        # Backup existing prompt
        try:
            with open("initial-prompt.txt", "r") as f:
                old_prompt = f.read()
            with open("initial-prompt.txt.backup", "w") as f:
                f.write(old_prompt)
        except FileNotFoundError:
            pass  # No backup needed if file doesn't exist
        
        # Write new prompt
        with open("initial-prompt.txt", "w") as f:
            f.write(new_prompt)
        
        return JSONResponse({
            "message": "System prompt updated successfully",
            "backup_created": True
        })
    except Exception as e:
        logger.error(f"Error updating system prompt: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/admin/context-config")
async def get_context_config(current_user: dict = Depends(require_admin)):
    """Get context-aware system configuration."""
    return JSONResponse({
        "enabled": context_builder.enabled,
        "mode": os.getenv("CONTEXT_AWARE_MODE", "disabled"),
        "template": os.getenv("CONTEXT_PROMPT_TEMPLATE", "minimal"),
        "config": context_builder.config
    })


@app.post("/admin/context-config")
async def update_context_config(
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """
    Update context-aware configuration.
    Note: Changes to CONTEXT_AWARE_MODE require restart to take effect.
    """
    try:
        data = await request.json()
        mode = data.get("mode")
        template = data.get("template")
        
        # Update .env file (requires restart)
        # For now, just return the values - actual .env update would require dotenv library
        
        return JSONResponse({
            "message": "Configuration updated. Note: Restart required for changes to take effect.",
            "current": {
                "mode": os.getenv("CONTEXT_AWARE_MODE", "disabled"),
                "template": os.getenv("CONTEXT_PROMPT_TEMPLATE", "minimal")
            },
            "requested": {
                "mode": mode,
                "template": template
            }
        })
    except Exception as e:
        logger.error(f"Error updating context config: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/admin/login-page", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Render admin login page."""
    return templates.TemplateResponse("admin_login.html", {"request": request})


# =============================================================================
# EXISTING PUBLIC ENDPOINTS
# =============================================================================



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
    
    print(user_message)

    response_logger.insert_message(session_id, "user", user_message)

    response = generate_from(full_prompt, project_id, location, endpoint_id)
    response_dict = response

    message_logger.log_message(user_message, session_id)
    
    response_logger.insert_message(session_id, "bot", response_dict['text'])

    return {'prompt': full_prompt, 'user_prompt': user_message, 'kai_response': response_dict['text'], 'model_version': response_dict['model_version'], 'history': "response_logger.select_all_messages(session_id)", 'tokens': response_dict['total_token_count']}


# main.py
from http.client import HTTPException
import os
import logging
import importlib.util
from random import sample
from typing import Optional
import sys

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response

import openai  # Corrected import
import tiktoken

from ai_configurator import AIConfigurator
from message_logger import MessageLogger
from context_manager import context_manager
from context_builder import context_builder
from llm_manager import llm_manager, LLMProvider
from auth import (
    verify_admin_credentials,
    get_current_user,
    require_admin
)
from token_manager import token_manager


import google.generativeai as genai
from google.cloud import aiplatform

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Import Buildly Labs Agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))
try:
    from buildly_labs.buildly_agent import enrich_user_message
    BUILDLY_AGENT_AVAILABLE = True
except ImportError:
    logger.warning("Buildly Labs agent module not available")
    BUILDLY_AGENT_AVAILABLE = False


# Initialize dependencies
ai_configurator = AIConfigurator()
message_logger = MessageLogger()

# Load prompt suggestions
try:
    with open("suggested-prompts.txt", "r") as new_file:
        prompt_list = new_file.readlines()
except FileNotFoundError:
    prompt_list = []

# Google Generative AI Configuration
# Check GOOGLE_API_KEY first (used in production), then GEMINI_API_KEY
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static and template mounting
templates = Jinja2Templates(directory="templates")


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
async def pre_user_prompt(current_user: dict = Depends(get_current_user)):
    """Fetch suggested prompts."""
    suggested_prompts = sample(prompt_list, min(3, len(prompt_list)))  # Fix for <3 prompts
    return JSONResponse(suggested_prompts)


@app.get("/post_response", response_class=JSONResponse)
async def post_response(keyword: str, current_user: dict = Depends(get_current_user)):
    """Fetch related news articles."""
    search_rss_feed = call_function_from_file("modules/buildly-collect", "news-blogs", "search_rss_feed")

    if callable(search_rss_feed):
        news = search_rss_feed(rss_url="https://www.buildly.io/news/feed/", keyword=keyword)
        return JSONResponse(news)
    
    return JSONResponse({"error": "Failed to fetch news"}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    """Render public index page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def test_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Render test chat UI (requires authentication)."""
    return templates.TemplateResponse("test.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat_view(request: Request):
    """Render chat UI (public access for web interface)."""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/api/config")
async def get_client_config():
    """
    Public endpoint to get client configuration.
    Provides the environment API token for chat UI.
    """
    env_token = os.getenv("API_KEY")
    return JSONResponse({
        "api_token": env_token,
        "has_token": env_token is not None
    })


@app.post("/chatbot")
async def chatbot(request: Request):
    """
    Chatbot endpoint - supports both authenticated API access and public web UI.
    Authentication is optional - if Authorization header provided, validates it.
    """
    # Optional authentication - check if Authorization header provided
    auth_header = request.headers.get("Authorization")
    user_info = {"authenticated": False, "type": "public", "sub": "web_ui"}
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        
        # Check env token first
        from auth import API_KEY
        if API_KEY and token == API_KEY:
            user_info = {"authenticated": True, "type": "api_key", "sub": "env_token"}
        # Then check database
        elif token_manager.verify_token(token):
            user_info = {"authenticated": True, "type": "api_key", "sub": "api_access"}
        # Invalid token provided
        else:
            raise HTTPException(status_code=401, detail="Invalid or expired API token")
    
    data = await request.json()
    # Accept both 'message' and 'prompt' for backward compatibility
    user_message = data.get("message") or data.get("prompt")
    
    # Get user-provided context (NEW: context-aware feature)
    user_context = data.get("context", {})
    
    # Context handling - support both full context and context hash
    context_hash = data.get("context_hash")
    user_id = user_info.get("sub", "web_ui")
    
    if context_hash:
        # Retrieve context from hash
        logger.info(f"Using context hash: {context_hash}")
        context_data = context_manager.resolve_context_hash(context_hash)
        
        if context_data:
            history = context_data.get("history", {"user": [], "bot": []})
            product_uuid = context_data.get("product_uuid")
        else:
            logger.warning(f"Context hash not found: {context_hash}, using defaults")
            history = {"user": [], "bot": []}
            product_uuid = None
    else:
        # Traditional approach - full context in request
        history = data.get("history")
        product_uuid = data.get("product_uuid")
        
        # Also check user_context for product_uuid (context-aware feature)
        if not product_uuid and user_context.get("product_uuid"):
            product_uuid = user_context["product_uuid"]
    
    tokens = data.get("tokens")
    
    # Ensure history has the correct structure - handle both list and dict formats
    if history is None or history == [] or not isinstance(history, dict):
        history = {"user": [], "bot": []}
    elif "user" not in history or "bot" not in history:
        logger.warning(f"History missing required keys, resetting to empty")
        history = {"user": [], "bot": []}
    
    # Prune history to stay within token limits
    history = context_manager.prune_history(history, max_tokens=2000)
    
    # Enrich user message with Buildly Labs product context (agentic capability)
    enriched_message = user_message
    product_context = {}
    
    if BUILDLY_AGENT_AVAILABLE:
        try:
            enriched_message, product_context = await enrich_user_message(user_message, product_uuid)
            if product_context.get("enabled") and product_context.get("product_info"):
                logger.info(f"Successfully enriched prompt with product context for UUID: {product_context.get('product_uuid')}")
        except Exception as e:
            logger.warning(f"Failed to enrich message with Buildly agent: {e}")
            # Continue with original message if agent fails

    llm = "gemini-2.0-flash" # specify the model you want to use
    provider = "gemini" # specify the provider for this model
    tokenizer = tiktoken.get_encoding("cl100k_base") # specify the tokenizer to use for this model
    tokenizer_function = lambda text: len(tokenizer.encode(text)) # specify the tokenizing function to use
    with open("initial-prompt.txt", "r") as prompt_file:
        initial_prompt = prompt_file.read().strip()
    
    # Load system constraints
    try:
        with open("system-constraints.txt", "r") as constraints_file:
            system_constraints = constraints_file.read().strip()
    except FileNotFoundError:
        system_constraints = ""

    # Build full prompt for LLM
    system_instruction = initial_prompt if initial_prompt else "You are a helpful AI assistant for Buildly Labs."
    
    # Combine system instruction with constraints
    full_system_prompt = system_instruction
    if system_constraints:
        full_system_prompt = f"{system_constraints}\n\n{system_instruction}"
    
    # CONTEXT-AWARE: Enhance system prompt with context (NEW)
    full_system_prompt = context_builder.build_context_prompt(
        base_prompt=full_system_prompt,
        context=user_context,
        product_context=product_context
    )
    
    # Format conversation history
    conversation_history = ""
    if history.get("user") and history.get("bot"):
        for user_msg, bot_msg in zip(history["user"], history["bot"]):
            conversation_history += f"User: {user_msg}\nAssistant: {bot_msg}\n"
    
    full_prompt = f"""{full_system_prompt}
    
    {conversation_history}
    
    User Question:
    {enriched_message}
    """

    try:
        # Use LLM manager with fallback capability
        result = llm_manager.generate(full_prompt)
        
        bot_response = result["response"]
        provider_used = result["provider"]
        model_used = result["model"]
        
        # Update conversation history
        history["user"].append(user_message)
        history["bot"].append(bot_response)
        
        # Create/update context hash for next request
        new_context_hash = context_manager.create_context_hash(
            user_id=user_id,
            product_uuid=product_uuid,
            history=history,
            metadata={
                "last_provider": provider_used,
                "last_model": model_used
            }
        )
        
        # Log the interaction with metadata
        message_logger.log_message(
            message=user_message,
            response=bot_response,
            provider=provider_used,
            model=model_used,
            tokens_used=tokens,
            metadata={
                "enriched": enriched_message != user_message,
                "product_uuid": product_context.get("product_uuid"),
                "user": user_id,
                "context_hash": new_context_hash
            }
        )
        
        # Build response
        chat_response = {
            "response": bot_response,
            "provider": provider_used,
            "model": model_used,
            "tokens": tokens,
            "context_hash": new_context_hash  # Return hash for next request
        }
        
        # Optionally add product context metadata to response
        if product_context.get("product_uuid"):
            chat_response["product_context"] = {
                "uuid": product_context.get("product_uuid"),
                "enriched": True
            }
        
        return JSONResponse(chat_response)
        
    except Exception as e:
        import traceback
        logger.error(f"Error in chatbot processing: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log the error with empty response
        message_logger.log_message(
            message=user_message,
            response=f"Error: {str(e)}",
            metadata={
                "error": str(e),
                "user": user_id
            }
        )
        
        return JSONResponse({"response": "Sorry... An error occurred."}, status_code=500)

# BabbleBeaver - Project Context

## Project Overview

An intelligent AI chatbot platform for Buildly Labs built with FastAPI, supporting multiple LLM providers with automatic fallback, comprehensive admin authentication system, and enhanced logging for model fine-tuning.

## Technology Stack

- **Backend**: FastAPI (Python 3.8+)
- **Frontend**: Jinja2 templates, vanilla JavaScript
- **LLM Providers**: Google Gemini, OpenAI, HuggingFace (extensible)
- **Authentication**: JWT tokens with bcrypt password hashing
- **Database**: SQLite (MessageLogger for conversation storage)
- **Deployment**: Uvicorn ASGI server
- **Operations**: Custom bash scripts for service management

## Current Features

### Admin Authentication System
- **Login/Logout**: Username/password authentication from .env
- **JWT Tokens**: Secure token-based API access
- **API Token Generation**: Long-lived tokens (1 year) for programmatic access
- **Protected Endpoints**: All chat and API endpoints require authentication
- **Admin Dashboard**: Web-based UI for management at `/admin`

### Multi-LLM Provider System
- **Automatic Fallback**: Priority-based provider switching on failure
- **Supported Providers**:
  - Google Gemini (gemini-2.0-flash)
  - OpenAI (gpt-4o-mini)
  - HuggingFace (infrastructure ready)
- **Dynamic Configuration**: Enable/disable providers via admin dashboard or .env
- **Real-time Testing**: Test LLM connections from admin panel
- **Priority System**: Lower priority number = tried first (0, 1, 2...)

### Enhanced Logging for Fine-tuning
- **Rich Metadata**: Logs include timestamp, provider, model, tokens, user, metadata
- **Filtering**: By date range, provider, user
- **Export**: JSONL format ready for model training
- **Analytics**: Usage statistics, token consumption, provider distribution
- **Database Schema**: Enhanced SQLite with indexes for performance

### Chat Interface
- **Conversational UI**: Clean chat interface at `/`
- **History Management**: Maintains conversation context
- **Product Context**: Integration with Buildly Labs agent for product-aware responses
- **Suggested Prompts**: Dynamic prompt suggestions
- **News Integration**: RSS feed integration for Buildly news

### Admin Dashboard Features
1. **Analytics Tab**: Total messages, average tokens, usage by provider
2. **Chat Logs Tab**: View/filter conversations, export for fine-tuning
3. **LLM Providers Tab**: Configure providers, test connections
4. **API Tokens Tab**: Generate and manage access tokens

### Operations Infrastructure
- **Startup Script** (`ops/startup.sh`): Complete service lifecycle management
  - Virtual environment setup and validation
  - Dependency installation and updates
  - Configuration validation (.env checks)
  - Database migration prompts
  - Start/stop/restart/status commands
  - Log viewing and monitoring
- **Process Management**: Background service with PID tracking
- **Log Capture**: Centralized logging to `ops/babblebeaver.log`

## API Endpoints

### Public Endpoints (No Auth Required)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/login-page` | GET | Admin login page |
| `/admin/login` | POST | Admin authentication |

### Protected Endpoints (Auth Required)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Chat interface |
| `/chatbot` | POST | Send message, get AI response |
| `/pre_user_prompt` | GET | Get suggested prompts |
| `/post_response` | GET | Get related news articles |
| `/admin` | GET | Admin dashboard |
| `/admin/generate-api-token` | POST | Generate API token |
| `/admin/logs` | GET | Retrieve chat logs |
| `/admin/logs/export` | GET | Export logs for fine-tuning |
| `/admin/logs/analytics` | GET | Get usage analytics |
| `/admin/llm/providers` | GET | List LLM providers |
| `/admin/llm/providers/{provider}/update` | POST | Update provider config |
| `/admin/llm/test` | POST | Test LLM connection |

## External Integrations

### Buildly Labs Agent
- **Purpose**: Enrich user messages with product context
- **API**: `enrich_user_message()` from `buildly_labs.buildly_agent`
- **Optional**: Graceful fallback if not available

### Google Gemini
- **Models**: gemini-2.0-flash (default), gemini-1.5-pro
- **API**: Google Generative AI SDK
- **Config**: GEMINI_API_KEY or GOOGLE_API_KEY

### OpenAI
- **Models**: gpt-4o-mini (default), gpt-4, gpt-3.5-turbo
- **API**: OpenAI Python SDK
- **Config**: OPENAI_API_KEY

### HuggingFace (Future)
- **Infrastructure**: Ready for implementation
- **Config**: HUGGINGFACE_AUTH_TOKEN

## Database Schema

### Messages Table (Enhanced)
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT NOT NULL,
    bot_response TEXT,
    provider TEXT,          -- 'gemini', 'openai', etc.
    model TEXT,             -- 'gemini-2.0-flash', 'gpt-4o-mini'
    tokens_used INTEGER,
    metadata TEXT           -- JSON: {user, enriched, error, product_uuid}
);

-- Indexes for performance
CREATE INDEX idx_timestamp ON messages(timestamp);
CREATE INDEX idx_provider ON messages(provider);
```

## File Organization

### Core Modules
- **`auth.py`** - JWT authentication, token generation/verification, admin auth
- **`llm_manager.py`** - Multi-provider LLM support with fallback logic
- **`message_logger.py`** - Enhanced logging with metadata and analytics
- **`ai_configurator.py`** - AI model configuration and response processing
- **`main.py`** - FastAPI app, routes, middleware, CORS configuration

### Frontend Templates
- **`templates/chat.html`** - Main chat interface
- **`templates/admin.html`** - Admin dashboard (analytics, logs, providers, tokens)
- **`templates/admin_login.html`** - Admin login page

### Static Assets
- **`static/style.css`** - UI styles
- **`static/script.js`** - Chat interface JavaScript

### Operations
- **`ops/startup.sh`** - Service management script (setup, start, stop, restart, status, logs)
- **`ops/README.md`** - Operations documentation
- **`ops/babblebeaver.pid`** - Process ID (auto-generated, gitignored)
- **`ops/babblebeaver.log`** - Application logs (auto-generated, gitignored)

### Utilities & Scripts
- **`setup_admin.py`** - Interactive setup wizard for .env configuration
- **`migrate_db.py`** - Database migration tool for schema upgrades

### Configuration
- **`.env`** - Environment variables (gitignored)
- **`example.env`** - Configuration template
- **`requirements.txt`** - Python dependencies

### Documentation
- **`README.md`** - Project overview
- **`SUMMARY.md`** - Quick overview of admin system
- **`QUICKSTART_ADMIN.md`** - Step-by-step setup guide
- **`ADMIN_README.md`** - Complete API documentation
- **`IMPLEMENTATION_SUMMARY.md`** - Detailed technical documentation
- **`INSTALLATION_CHECKLIST.md`** - Verification checklist
- **`OPS_QUICKSTART.md`** - Operations quick reference

### Buildly Labs Integration
- **`modules/buildly_labs/`** - Buildly Labs agent module
  - `buildly_agent.py` - Product context enrichment
  - `test_agent.py` - Agent tests
  - Documentation files (ARCHITECTURE.md, EXAMPLES.md, etc.)

## Key Patterns

### Authentication Flow
```python
# 1. Login and get token
POST /admin/login
{
  "username": "admin",
  "password": "password"
}
# Returns: {"access_token": "jwt_token", "token_type": "bearer"}

# 2. Use token in subsequent requests
GET/POST /any-endpoint
Headers: {
  "Authorization": "Bearer jwt_token"
}
```

### LLM Fallback Pattern
```python
# LLM Manager tries providers in priority order
providers = [
    LLMConfig(provider="gemini", priority=0, enabled=True),
    LLMConfig(provider="openai", priority=1, enabled=True),
]

# Request handling
try:
    result = llm_manager.generate(prompt)
    # Uses Gemini (priority 0)
except:
    # Automatically tries OpenAI (priority 1)
    pass
```

### Logging Pattern
```python
# Enhanced logging with metadata
message_logger.log_message(
    message=user_message,
    response=bot_response,
    provider="gemini",
    model="gemini-2.0-flash",
    tokens_used=150,
    metadata={
        "user": "api_access",
        "enriched": True,
        "product_uuid": "uuid-here"
    }
)
```

### Protected Route Pattern
```python
from fastapi import Depends
from auth import get_current_user, require_admin

@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    # Any authenticated user can access
    return {"user": current_user["sub"]}

@app.post("/admin/action")
async def admin_route(current_user: dict = Depends(require_admin)):
    # Only admin users can access
    return {"status": "ok"}
```

## Environment Variables

```bash
# CORS Configuration
CORS_ALLOWED_DOMAINS=http://localhost:8000,http://localhost:3000,https://your-domain.com

# LLM API Keys
OPENAI_API_KEY=sk_...
GEMINI_API_KEY=...
GOOGLE_API_KEY=...  # Alternative to GEMINI_API_KEY
HUGGINGFACE_AUTH_TOKEN=hf_...

# LLM Provider Configuration
GEMINI_MODEL=gemini-2.0-flash
GEMINI_PRIORITY=0
GEMINI_ENABLED=true

OPENAI_MODEL=gpt-4o-mini
OPENAI_PRIORITY=1
OPENAI_ENABLED=true

HUGGINGFACE_MODEL=meta-llama/Llama-2-7b-chat-hf
HUGGINGFACE_PRIORITY=2
HUGGINGFACE_ENABLED=false

# Admin Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# JWT Configuration
JWT_SECRET_KEY=your-generated-secret-key
ACCESS_TOKEN_EXPIRE_HOURS=24

# Buildly Labs Agent
BUILDLY_AGENT=true
BUILDLY_API_BASE_URL=https://labs-api.buildly.io
BUILDLY_AUTH_TOKEN=...

# Application
INITIAL_PROMPT_FILE_PATH=initial-prompt.txt
```

## Development Commands

```bash
# Using the startup script (recommended)
./ops/startup.sh setup      # First time setup
./ops/startup.sh start      # Start service
./ops/startup.sh stop       # Stop service
./ops/startup.sh restart    # Restart service
./ops/startup.sh status     # Check status
./ops/startup.sh logs       # Follow logs

# Manual commands
python setup_admin.py       # Interactive .env setup
python migrate_db.py        # Migrate database
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Testing
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

## Recent Changes (Latest)

### Operations Infrastructure (Dec 7, 2025)
- ✅ Created `ops/startup.sh` service management script
- ✅ Added virtual environment automation
- ✅ Implemented dependency checking and updates
- ✅ Added configuration validation
- ✅ Built start/stop/restart/status/logs commands
- ✅ Process management with PID tracking
- ✅ Centralized logging to ops/babblebeaver.log
- ✅ Full documentation in `ops/README.md` and `OPS_QUICKSTART.md`

### CORS Configuration Enhancement (Dec 7, 2025)
- ✅ Updated CORS middleware with explicit origins
- ✅ Added localhost support (ports 8000, 3000)
- ✅ Added 127.0.0.1 variants
- ✅ Environment variable configuration support
- ✅ Specific HTTP method allowlist (GET, POST, PUT, DELETE, OPTIONS)
- ✅ Credentials support enabled

### Admin Authentication System (Dec 7, 2025)
- ✅ Created comprehensive JWT authentication system
- ✅ Built admin dashboard with 4 tabs (analytics, logs, providers, tokens)
- ✅ Implemented API token generation for automation
- ✅ Added protected endpoints with authentication middleware
- ✅ Created login/admin UI templates
- ✅ Full documentation suite created

### Multi-LLM Provider System (Dec 7, 2025)
- ✅ Built LLM manager with automatic fallback
- ✅ Added support for Gemini, OpenAI, HuggingFace
- ✅ Implemented priority-based provider selection
- ✅ Created admin interface for provider management
- ✅ Added real-time connection testing

### Enhanced Logging System (Dec 7, 2025)
- ✅ Upgraded database schema with metadata
- ✅ Added filtering by date, provider, user
- ✅ Implemented JSONL export for fine-tuning
- ✅ Created analytics dashboard
- ✅ Added database migration tool

## Known Issues & Limitations

1. **HuggingFace Integration**: Infrastructure ready but inference not yet implemented
2. **Static File Protection**: Basic authentication implemented but may need refinement
3. **Rate Limiting**: Not yet implemented (recommended for production)
4. **Multi-user Admin**: Currently single admin user (can be extended)
5. **Password Reset**: Not implemented (must edit .env manually)
6. **Token Revocation**: No token blacklist (tokens valid until expiry)
7. **Audit Logging**: Admin actions not separately logged
8. **Database Backups**: Manual only (no automated backups)

## Testing Strategy

Currently, testing is primarily manual through:
- Admin dashboard UI testing
- API endpoint testing with curl
- LLM provider testing via admin panel
- Log export validation

**Future improvements**:
- Add pytest-based integration tests
- Add unit tests for auth module
- Add LLM manager unit tests
- Add message logger tests
- CI/CD pipeline with automated tests

## Security Considerations

**Implemented**:
- ✅ JWT-based authentication
- ✅ Password hashing with bcrypt
- ✅ Token expiration (24h for access, 1y for API)
- ✅ Protected API endpoints
- ✅ Credentials in .env (gitignored)
- ✅ CORS with explicit origins
- ✅ Session-based admin access

**Recommended for Production**:
- ⚠️ Enable HTTPS/TLS
- ⚠️ Implement rate limiting
- ⚠️ Add IP whitelisting for admin
- ⚠️ Set up token rotation
- ⚠️ Add audit logging
- ⚠️ Implement MFA for admin
- ⚠️ Use secrets manager (not .env)
- ⚠️ Regular security audits

## Next Priorities

1. ✅ **COMPLETED**: Operations infrastructure with startup script
2. ✅ **COMPLETED**: CORS configuration for local/production testing
3. **Testing Suite**: Add pytest-based tests
4. **HuggingFace**: Complete inference implementation
5. **Rate Limiting**: Add to protect API endpoints
6. **Documentation**: Add API client examples in multiple languages
7. **Monitoring**: Add health check endpoint
8. **Backups**: Automated database backup system
9. **Multi-tenancy**: Support for multiple organizations/teams
10. **WebSocket**: Real-time chat updates

## Development Workflow

Following "The Buildly Way":

1. **Feature Development**:
   - Create/modify modules in root directory
   - Update templates as needed
   - Register routes in `main.py`
   - Update this context document
   - Document in appropriate README files

2. **Testing**:
   - Manual testing via admin dashboard
   - API testing with curl/Postman
   - Check logs in `ops/babblebeaver.log`
   - Verify authentication flows

3. **Documentation**:
   - Keep root docs up to date (README.md, SUMMARY.md)
   - Update feature-specific docs (ADMIN_README.md, etc.)
   - Update this project-context.md
   - Only create summary docs at end of major features

4. **Operations**:
   - Use `ops/startup.sh` for all service management
   - Monitor logs via `./ops/startup.sh logs`
   - Check status with `./ops/startup.sh status`
   - Clean restarts with `./ops/startup.sh restart`

## Quick Reference

### Service Management
```bash
./ops/startup.sh setup      # Setup environment
./ops/startup.sh start      # Start service
./ops/startup.sh stop       # Stop service
./ops/startup.sh restart    # Restart service
./ops/startup.sh status     # Check status
./ops/startup.sh logs       # Follow logs
```

### Access Points
- **Chat**: http://localhost:8000
- **Admin**: http://localhost:8000/admin/login-page
- **API Docs**: http://localhost:8000/docs

### Common Tasks
```bash
# Generate API token
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass"}' \
  | jq -r '.access_token'

# Export logs for fine-tuning
curl "http://localhost:8000/admin/logs/export?format=jsonl" \
  -H "Authorization: Bearer TOKEN" \
  -o training_data.jsonl

# Test LLM connection
curl -X POST http://localhost:8000/admin/llm/test \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test","provider":"gemini"}'
```

---

**Last Updated**: December 7, 2025  
**Current Version**: 1.0.0  
**Maintained By**: Buildly Labs

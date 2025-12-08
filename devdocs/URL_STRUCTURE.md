# BabbleBeaver - URL Structure Update

## Summary of Changes

The BabbleBeaver application now has three distinct pages with proper authentication controls:

### Public Pages (No Authentication Required)

**1. Index Page - `/`**
- **URL**: http://localhost:8004/
- **File**: `templates/index.html`
- **Purpose**: Public-facing landing page about Buildly, Open Build, and BabbleBeaver
- **Features**:
  - Overview of BabbleBeaver features
  - Information about Buildly platform
  - Information about Open Build initiative
  - Links to GitHub repository: https://www.github.com/open-build/babblebeaver
  - Modern, responsive design with gradient background

### Authenticated Pages (Require API Key)

**2. Test Chat Page - `/test`**
- **URL**: http://localhost:8004/test
- **File**: `templates/test.html`
- **Purpose**: Simple test interface for the chatbot API
- **Authentication**: Requires Bearer token (API key) in Authorization header
- **Features**:
  - Prompts for API key on first visit (stored in session storage)
  - Simple chat interface for testing
  - Suggested prompts for quick testing
  - Direct API integration

**3. Chat Page - `/chat`** (Legacy)
- **URL**: http://localhost:8004/chat
- **File**: `templates/chat.html`
- **Purpose**: Original chat interface (kept for backward compatibility)
- **Authentication**: Requires Bearer token (API key)

**4. Admin Dashboard - `/admin`**
- **URL**: http://localhost:8004/admin
- **File**: `templates/admin.html`
- **Purpose**: Full admin interface
- **Authentication**: Requires Bearer token (API key)
- **New Feature**: Now includes a "🧪 Test Chat" button in the header that links to `/test`

## Admin Dashboard Enhancement

The admin dashboard now has a convenient link to the test chat interface:
- Located in the header next to the "Logout" button
- Opens in a new tab for easy testing without leaving the admin interface
- Only visible when authenticated

## Routes Added/Modified

```python
# Public route - no authentication
@app.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    """Render public index page."""
    return templates.TemplateResponse("index.html", {"request": request})

# Authenticated test page
@app.get("/test", response_class=HTMLResponse)
async def test_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Render test chat UI (requires authentication)."""
    return templates.TemplateResponse("test.html", {"request": request})

# Legacy chat page (kept for compatibility)
@app.get("/chat", response_class=HTMLResponse)
async def chat_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Render chat UI (legacy route, requires authentication)."""
    return templates.TemplateResponse("chat.html", {"request": request})
```

## Files Created/Modified

### Created:
1. `templates/index.html` - Public landing page
2. `templates/test.html` - Test chat interface

### Modified:
1. `templates/admin.html` - Added "Test Chat" button link
2. `main.py` - Updated routes (changed `/` to public, added `/test` and `/chat`)

## Usage

### For Public Visitors:
1. Visit http://localhost:8004/
2. Learn about BabbleBeaver, Buildly, and Open Build
3. Click GitHub link to view the source code

### For Authenticated Users:
1. Log in to admin: http://localhost:8004/admin/login-page
2. Use credentials from `.env` file
3. Click "🧪 Test Chat" button in admin header
4. Test the chatbot API directly

### For API Testing:
1. Visit http://localhost:8004/test
2. Enter your API key (from .env: `aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck`)
3. Test the chatbot functionality

## Current API Key
```
API_KEY=aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck
```

## Testing the Changes

```bash
# Test public index page (no auth required)
curl http://localhost:8004/

# Test authenticated routes (requires API key)
curl -H "Authorization: Bearer aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck" http://localhost:8004/test
curl -H "Authorization: Bearer aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck" http://localhost:8004/chat
```

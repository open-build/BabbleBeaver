# Testing BabbleBeaver with Production Environment Variables

## Summary

Your production deployment uses **Vertex AI** (Google Cloud Platform's managed AI service), not the standard Gemini API. I've updated the code to support both.

## Changes Made

### 1. Updated `llm_manager.py`
- ✅ Added Vertex AI support (auto-detects based on `PROJECT_ID` environment variable)
- ✅ Falls back to standard Gemini API if `PROJECT_ID` is not set
- ✅ Uses `VERTEX_MODEL_NAME` when running on Vertex AI

### 2. Updated `example.env`
- ✅ Added Vertex AI configuration variables
- ✅ Documented production CORS domains

### 3. Created `.env.production.example`
- ✅ Template with your exact production values (for reference)

## Required Dependencies

The `google-cloud-aiplatform` package is already in your `requirements.txt` ✅

## To Test Locally with Production Settings

Add these variables to your `.env` file:

```bash
# Google Cloud / Vertex AI Configuration
PROJECT_ID=dev-buildly
LOCATION=us-west1
VERTEX_MODEL_NAME=gemini-2.0-flash-exp

# Google API Key (for Vertex AI authentication)
GOOGLE_API_KEY=AIzaSyCp9B9z7AonqKzzGsaNRK1au_3ah5_1-pM

# Buildly Agent (already configured, just update token)
BUILDLY_AGENT=true
BUILDLY_API_BASE_URL=https://labs-api.buildly.io
BUILDLY_AUTH_TOKEN=62e330ab93b10e9c0a3dbe1a5f739d79547f30eb

# CORS - Add production domains
CORS_ALLOWED_DOMAINS=http://localhost,https://localhost,http://labs.buildly.io,https://labs.buildly.io,http://labs-release.buildly.io,https://labs-release.buildly.io

# JWT - Set to 0 for never-expiring tokens (as requested)
ACCESS_TOKEN_EXPIRE_HOURS=0
```

## Environment Variables Mapping

| Production Variable | Status | Notes |
|-------------------|--------|-------|
| `PROJECT_ID` | ✅ **NEW** | Triggers Vertex AI mode |
| `LOCATION` | ✅ **NEW** | GCP region (us-west1) |
| `VERTEX_MODEL_NAME` | ✅ **NEW** | Gemini model for Vertex AI |
| `GOOGLE_API_KEY` | ✅ Existing | Already supported |
| `BUILDLY_AGENT` | ✅ Existing | Already supported |
| `BUILDLY_API_BASE_URL` | ✅ Existing | Already supported |
| `BUILDLY_AUTH_TOKEN` | ✅ Existing | Already supported |
| `CORS_ALLOWED_DOMAINS` | ✅ Existing | Already supported |

## How It Works

### Standard Gemini API (Development)
If `PROJECT_ID` is **not set** in `.env`:
```python
# Uses google-generativeai library
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
```

### Vertex AI (Production)
If `PROJECT_ID` **is set** in `.env`:
```python
# Uses vertexai library
vertexai.init(project="dev-buildly", location="us-west1")
model = GenerativeModel("gemini-2.0-flash-exp")
```

## Testing Steps

1. **Update your `.env` file** with the production variables above

2. **Restart the application**:
   ```bash
   ./ops/startup.sh restart
   ```

3. **Check the logs** for Vertex AI initialization:
   ```bash
   ./ops/startup.sh logs
   ```
   
   You should see:
   ```
   Initializing Vertex AI with project: dev-buildly, location: us-west1
   ```

4. **Test the chat endpoint**:
   ```bash
   # Login first
   TOKEN=$(curl -X POST http://localhost:8000/admin/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"changeme123"}' \
     | jq -r '.access_token')
   
   # Test chat with Vertex AI
   curl -X POST http://localhost:8000/chatbot \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message":"Hello, testing Vertex AI!"}'
   ```

5. **Verify in admin dashboard**:
   - Go to http://localhost:8000/admin
   - Check "LLM Providers" tab
   - Should show Gemini using Vertex AI

## Important Notes

### ⚠️ Authentication for Vertex AI

When using Vertex AI in production on Google Cloud, you typically use **Application Default Credentials (ADC)** instead of API keys. The code will work with either:

1. **API Key** (current setup): Uses `GOOGLE_API_KEY`
2. **ADC** (production GKE): Automatic if running on GCP with proper IAM roles

### 🔐 Security Considerations

- The production `GOOGLE_API_KEY` is exposed in the Kubernetes config you shared
- Consider using **Google Secret Manager** or Kubernetes secrets instead
- The `BUILDLY_AUTH_TOKEN` should also be in secrets, not plaintext

### 💡 Token Expiration

As requested, tokens are now set to **never expire** when `ACCESS_TOKEN_EXPIRE_HOURS=0`:
- Login tokens: Never expire
- API tokens: Can be set to never expire (pass `expires_days: 0` when generating)

## Next Steps

1. ✅ Add production variables to your local `.env`
2. ✅ Test locally with Vertex AI
3. ✅ Verify logs show "Initializing Vertex AI"
4. ✅ Test chat functionality
5. Consider migrating API keys to secret manager for production

## Files Reference

- **`.env`** - Your local environment (update this)
- **`example.env`** - Template for new developers
- **`.env.production.example`** - Production values reference (do not commit!)
- **`llm_manager.py`** - Updated with Vertex AI support
- **`requirements.txt`** - Already has google-cloud-aiplatform

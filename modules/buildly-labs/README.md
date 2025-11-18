# Buildly Labs Agent Module

This module provides **agentic capabilities** for the BabbleBeaver chatbot by integrating with the Buildly Labs API to fetch real-time product information.

## Features

- 🚀 **Async/Parallel Fetching**: Queries product info, features, and releases simultaneously to minimize latency
- 🔍 **Automatic UUID Detection**: Extracts `product_uuid` from user messages automatically
- 🎯 **Selective Enrichment**: Only activates when BUILDLY_AGENT is enabled
- ⚡ **Non-Blocking**: Designed to not slow down API responses
- 🛡️ **Fault Tolerant**: Gracefully handles API failures without breaking the chatbot

## How It Works

### 1. Agentic Behavior

When a user message contains a `product_uuid`, the agent:
1. Detects the UUID using pattern matching
2. Fires parallel async requests to fetch:
   - Product basic information
   - Product features
   - Product releases
3. Formats the data into context
4. Enriches the AI prompt with real product data
5. Returns enhanced response to the user

## Configuration

Add to your `.env` file:

```bash
# Enable the Buildly Labs agent
BUILDLY_AGENT=true

# Optional: Override default API URL
BUILDLY_API_BASE_URL=https://labs-api.buildly.io

# Required: Django authentication token from Buildly Labs
BUILDLY_AUTH_TOKEN=your-django-auth-token-here
```

**To get your auth token:**
1. Log in to https://labs.buildly.io
2. Navigate to your account settings or API section
3. Copy your Django authentication token
4. Add it to your `.env` file

### 3. Usage

#### Automatic Detection

The agent automatically detects product UUIDs in messages:

```
User: "Tell me about product_uuid: 123e4567-e89b-12d3-a456-426614174000"
```

#### Explicit Parameter

You can also pass `product_uuid` in the request body:

```json
{
  "prompt": "What are the latest features?",
  "product_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "history": {...},
  "tokens": 0
}
```

### 4. API Endpoints Queried

The agent queries these Buildly Labs API endpoints:

- `GET /products/{product_uuid}` - Basic product information
- `GET /products/{product_uuid}/features` - Product features list
- `GET /products/{product_uuid}/releases` - Product releases/versions

### 5. Performance

- **Timeout**: 5 seconds per endpoint (configurable)
- **Parallel Execution**: All 3 endpoints queried simultaneously
- **Total Overhead**: ~5 seconds max (not 15 seconds)
- **Fallback**: If agent fails, chatbot continues with original message

## Architecture

```
User Message
    ↓
Extract product_uuid (regex pattern matching)
    ↓
[Async Parallel Fetching]
    ├→ GET /products/{uuid}
    ├→ GET /products/{uuid}/features
    └→ GET /products/{uuid}/releases
    ↓
Format Context (structured text)
    ↓
Enrich AI Prompt
    ↓
Generate Response (with product context)
    ↓
Return to User
```

## Example Enriched Prompt

Original message:
```
"What are the new features in product_uuid: abc-123?"
```

Enriched prompt sent to AI:
```
What are the new features in product_uuid: abc-123?

--- BUILDLY LABS PRODUCT CONTEXT ---
Product Information:
  - name: BabbleBeaver
  - version: 2.0.1
  - description: AI-powered chatbot platform

Product Features:
  1. Multi-model Support
     Supports OpenAI, Gemini, and custom models
  2. Conversation History
     Token-aware history management
  3. Agentic Integration
     Real-time product data enrichment

Product Releases:
  1. Version 2.0.1
     Released: 2025-01-15
     Notes: Bug fixes and performance improvements

--- END PRODUCT CONTEXT ---
```

## Error Handling

The agent is designed to fail gracefully:

- **Module Import Fails**: Chatbot continues without agent
- **API Timeout**: Returns None, chatbot uses original message
- **HTTP Errors**: Logged as warnings, chatbot continues
- **Invalid UUID**: Agent skips enrichment, proceeds normally

## Testing

Test if the agent is enabled:

```python
from modules.buildly_labs.buildly_agent import get_agent

agent = get_agent()
print(f"Agent enabled: {agent.enabled}")
print(f"Base URL: {agent.base_url}")
```

Test UUID extraction:

```python
from modules.buildly_labs.buildly_agent import BuildlyAgent

text = "Check product_uuid: 123e4567-e89b-12d3-a456-426614174000"
uuid = BuildlyAgent.extract_product_uuid(text)
print(f"Extracted UUID: {uuid}")
```

## Disabling the Agent

To disable the agent without removing code:

```bash
# In .env
BUILDLY_AGENT=false
```

Or simply don't set the environment variable (disabled by default).

## Future Enhancements

- [ ] Cache product data to reduce API calls
- [ ] Support multiple product UUIDs in one message
- [ ] Add user authentication for private products
- [ ] Implement retry logic with exponential backoff
- [ ] Add metrics/analytics for agent usage

## License

Same as BabbleBeaver project

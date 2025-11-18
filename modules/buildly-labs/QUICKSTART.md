# Buildly Labs Agent - Quick Reference

## Setup (30 seconds)

1. **Enable the agent** in `.env`:
   ```bash
   BUILDLY_AGENT=true
   BUILDLY_API_BASE_URL=https://labs-api.buildly.io
   ```

2. **Restart your server**:
   ```bash
   uvicorn main:app --reload
   ```

## How It Works

```
User message with product_uuid
         ↓
Agent auto-detects UUID
         ↓
Parallel API calls (5s max):
  • /products/{uuid}
  • /products/{uuid}/features  
  • /products/{uuid}/releases
         ↓
Prompt enrichment
         ↓
AI generates enhanced response
```

## Two Ways to Use

### Method 1: UUID in Message (Automatic)
```json
{
  "prompt": "Tell me about product_uuid: abc-123-def",
  "history": {...},
  "tokens": 0
}
```

### Method 2: Explicit Parameter (Recommended)
```json
{
  "prompt": "What are the features?",
  "product_uuid": "abc-123-def",
  "history": {...},
  "tokens": 0
}
```

## UUID Patterns Recognized

✅ `product_uuid: 123e4567-e89b-12d3-a456-426614174000`
✅ `product_uuid=123e4567-e89b-12d3-a456-426614174000`
✅ `"product_uuid": "123e4567-e89b-12d3-a456-426614174000"`

## API Endpoints Called

| Endpoint | Data Retrieved |
|----------|----------------|
| `/products/{uuid}` | Name, description, version |
| `/products/{uuid}/features` | Feature list with descriptions |
| `/products/{uuid}/releases` | Version history, release notes |

## Response Format

```json
{
  "response": "AI response with product context",
  "usedTokens": 150,
  "updatedHistory": null,
  "product_context": {
    "uuid": "abc-123-def",
    "enriched": true
  }
}
```

## Performance

- ⚡ **Timeout**: 5 seconds max per endpoint
- 🔄 **Parallel fetching**: All endpoints queried simultaneously
- 📊 **Total overhead**: ~5 seconds (not 15!)
- 🛡️ **Fault tolerant**: Fails gracefully, chatbot continues

## Testing

```bash
# Quick test
curl -X POST http://localhost:8000/chatbot \
  -H "Content-Type: application/json" \
  -d '{"prompt": "product_uuid: test-123", "history": {"user":[], "bot":[]}, "tokens": 0}'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent not working | Check `BUILDLY_AGENT=true` in `.env` |
| Invalid UUID | Use format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| Slow responses | Reduce timeout or implement caching |
| No product data | Verify UUID exists in Buildly Labs API |

## Files Created

```
modules/buildly-labs/
├── __init__.py              # Module initialization
├── buildly_agent.py         # Main agent implementation
├── test_agent.py            # Test script
├── README.md                # Full documentation
└── EXAMPLES.md              # Usage examples
```

## Configuration Options

```python
# In buildly_agent.py __init__:
BuildlyAgent(
    base_url="https://labs-api.buildly.io",  # API base URL
    timeout=5.0                                # Request timeout
)
```

## Disable Agent

Set in `.env`:
```bash
BUILDLY_AGENT=false
```

Or simply remove/comment the line.

## Key Features

✅ **Agentic**: Autonomously fetches and enriches context
✅ **Async**: Non-blocking parallel requests
✅ **Fast**: Optimized for minimal latency
✅ **Resilient**: Graceful error handling
✅ **Flexible**: Multiple UUID detection methods
✅ **Observable**: Detailed logging
✅ **Self-contained**: Modular design

## Next Steps

1. Read [modules/buildly-labs/README.md](README.md) for full docs
2. Check [modules/buildly-labs/EXAMPLES.md](EXAMPLES.md) for code samples
3. Run `python modules/buildly-labs/test_agent.py` to test
4. Monitor logs to see agent in action

---

**Made with ❤️ for Buildly Labs**

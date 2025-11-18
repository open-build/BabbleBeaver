# Buildly Labs Agent - Usage Examples

This document provides practical examples of how to use the Buildly Labs Agent in BabbleBeaver.

## Example 1: Basic Product Query

### User sends:
```json
{
  "prompt": "What features does product_uuid: 123e4567-e89b-12d3-a456-426614174000 have?",
  "history": {"user": [], "bot": []},
  "tokens": 0
}
```

### What happens:
1. Agent detects UUID: `123e4567-e89b-12d3-a456-426614174000`
2. Fetches data from:
   - `/products/123e4567-e89b-12d3-a456-426614174000`
   - `/products/123e4567-e89b-12d3-a456-426614174000/features`
   - `/products/123e4567-e89b-12d3-a456-426614174000/releases`
3. Enriches the prompt with product context
4. AI generates response based on real data

### Response includes:
```json
{
  "response": "Based on the latest information, this product has the following features: ...",
  "usedTokens": 150,
  "updatedHistory": null,
  "product_context": {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "enriched": true
  }
}
```

## Example 2: Explicit Product UUID Parameter

### User sends:
```json
{
  "prompt": "What's new in the latest release?",
  "product_uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "history": {"user": [], "bot": []},
  "tokens": 0
}
```

### What happens:
- Agent uses the explicit `product_uuid` parameter
- No need to include UUID in the message text
- Same enrichment process occurs

## Example 3: Multiple Message Patterns

The agent recognizes various UUID patterns:

### Pattern 1: Colon notation
```
"Tell me about product_uuid: 123e4567-e89b-12d3-a456-426614174000"
```

### Pattern 2: Equals sign
```
"Show features for product_uuid=123e4567-e89b-12d3-a456-426614174000"
```

### Pattern 3: JSON-style
```
"Get info on \"product_uuid\": \"123e4567-e89b-12d3-a456-426614174000\""
```

### Pattern 4: Natural language
```
"What do you know about product 123e4567-e89b-12d3-a456-426614174000?"
```
_(This requires the UUID to be in valid format)_

## Example 4: Frontend Integration

### JavaScript/jQuery Example

```javascript
// Send message with product UUID
function sendMessageWithProduct(message, productUuid = null) {
  const payload = {
    prompt: message,
    history: JSON.parse(sessionStorage.getItem("messageHistory")) || {"user": [], "bot": []},
    tokens: JSON.parse(sessionStorage.getItem("totalUsedTokens")) || 0
  };
  
  // Add product UUID if provided
  if (productUuid) {
    payload.product_uuid = productUuid;
  }
  
  $.ajax({
    url: '/chatbot',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(payload),
    success: function(data) {
      const { response, usedTokens, product_context } = data;
      
      // Display response
      displayMessage(response, 'bot');
      
      // Show product context indicator if enriched
      if (product_context && product_context.enriched) {
        showProductBadge(product_context.uuid);
      }
      
      // Update session storage
      sessionStorage.setItem("totalUsedTokens", JSON.stringify(usedTokens));
    },
    error: function(error) {
      console.error("Error:", error);
    }
  });
}

// Usage examples:

// Example 1: UUID in message
sendMessageWithProduct("What features does product_uuid: abc-123 have?");

// Example 2: Explicit UUID parameter
sendMessageWithProduct("Tell me about the latest features", "abc-123");

// Example 3: Product selector dropdown
$('#product-selector').on('change', function() {
  const selectedUuid = $(this).val();
  sendMessageWithProduct("What's new?", selectedUuid);
});
```

## Example 5: Python SDK Usage

If you're building a Python client for BabbleBeaver:

```python
import httpx
import asyncio

async def chat_with_product(message: str, product_uuid: str = None):
    """Send a chat message with optional product context."""
    
    payload = {
        "prompt": message,
        "history": {"user": [], "bot": []},
        "tokens": 0
    }
    
    if product_uuid:
        payload["product_uuid"] = product_uuid
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/chatbot",
            json=payload
        )
        return response.json()

# Usage
async def main():
    # Example 1: Automatic UUID detection
    result1 = await chat_with_product(
        "Tell me about product_uuid: 123e4567-e89b-12d3-a456-426614174000"
    )
    print(result1['response'])
    
    # Example 2: Explicit UUID
    result2 = await chat_with_product(
        "What are the latest features?",
        product_uuid="f47ac10b-58cc-4372-a567-0e02b2c3d479"
    )
    print(result2['response'])
    
    # Check if product context was used
    if result2.get('product_context', {}).get('enriched'):
        print(f"Response enriched with product {result2['product_context']['uuid']}")

asyncio.run(main())
```

## Example 6: Testing the Agent

### Test Script

```bash
# Navigate to the agent module
cd modules/buildly-labs

# Run the test script
python test_agent.py
```

### Manual Testing with cURL

```bash
# Test with UUID in message
curl -X POST http://localhost:8000/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What features does product_uuid: 123e4567-e89b-12d3-a456-426614174000 have?",
    "history": {"user": [], "bot": []},
    "tokens": 0
  }'

# Test with explicit UUID parameter
curl -X POST http://localhost:8000/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Tell me about the latest release",
    "product_uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "history": {"user": [], "bot": []},
    "tokens": 0
  }'
```

## Example 7: Error Handling

### When agent is disabled:
```json
{
  "prompt": "product_uuid: 123-456",
  "history": {"user": [], "bot": []},
  "tokens": 0
}
```

**Result**: Normal chatbot response without product enrichment.

### When API fails:
```json
{
  "prompt": "product_uuid: invalid-uuid",
  "history": {"user": [], "bot": []},
  "tokens": 0
}
```

**Result**: Chatbot continues with original message, logs warning.

### When timeout occurs:
- Agent has 5-second timeout per endpoint
- If timeout occurs, returns None gracefully
- Chatbot proceeds without enrichment
- No error shown to user

## Performance Considerations

### Latency Impact

Without agent:
```
User message → AI processing → Response
(~2-3 seconds)
```

With agent (parallel fetching):
```
User message → [Agent fetch (5s max) || AI processing] → Response
(~5-7 seconds total, not 15 seconds!)
```

### Optimization Tips

1. **Enable only when needed**: Set `BUILDLY_AGENT=true` only in production
2. **Cache responses**: Consider adding Redis caching for frequently queried products
3. **Adjust timeout**: Reduce timeout to 3s for faster responses with acceptable failure rate
4. **Pre-fetch**: If you know the product UUID, send it with the first message

## Best Practices

1. **Always provide product_uuid explicitly** when possible (faster than pattern matching)
2. **Use valid UUID format** (8-4-4-4-12 hexadecimal)
3. **Monitor logs** to see agent activity and any failures
4. **Set reasonable timeouts** based on your API response times
5. **Handle product_context in responses** to give users feedback about enrichment

## Troubleshooting

### Agent not enriching messages?

1. Check `.env` has `BUILDLY_AGENT=true`
2. Verify UUID format is correct
3. Check API endpoint is accessible
4. Review logs for timeout/error messages

### Slow responses?

1. Reduce timeout in `BuildlyAgent` initialization
2. Check Buildly Labs API response times
3. Consider implementing caching
4. Use explicit `product_uuid` parameter instead of pattern matching

### Getting None for product data?

1. Verify the product UUID exists in the API
2. Check API endpoint URLs are correct
3. Review authentication if required
4. Check network connectivity

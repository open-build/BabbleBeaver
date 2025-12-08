# BabbleBeaver API Response Structure

## Chatbot Endpoint

**Endpoint**: `POST /chatbot`

**Authentication**: Required (Bearer token in Authorization header)

---

## Request Format

```json
{
  "message": "Your question here",
  "history": {
    "user": ["previous user message"],
    "bot": ["previous bot response"]
  },
  "tokens": 150,
  "product_uuid": "optional-product-id",
  "context_hash": "optional-session-hash"
}
```

**Request Fields**:
- `message` (string, required): The user's question or prompt
  - Alternative: `prompt` (accepted for backward compatibility)
- `history` (object, optional): Conversation history
  - `user` (array): Previous user messages
  - `bot` (array): Previous bot responses
  - **Note**: Can be omitted if using `context_hash`
  - **Still works!** Use this if you prefer stateless/traditional approach
- `tokens` (number, optional): Token limit for response
- `product_uuid` (string, optional): Product context identifier
- **`context_hash` (string, optional)**: ⭐ **Performance optimization (completely optional!)**
  - **Server creates this**, frontend just echoes it back
  - Use for conversations with 3+ exchanges
  - Reduces payload by 69-98% for longer conversations
  - **First 1-2 messages: 0% benefit** - skip it for short interactions
  - See [Context Optimization Guide](CONTEXT_OPTIMIZATION.md) for when to use

---

## Response Format

### Success Response (HTTP 200)

```json
{
  "response": "The AI-generated response text goes here",
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "tokens": 150,
  "context_hash": "a1b2c3d4e5f6g7h8",
  "product_context": {
    "uuid": "product-uuid-here",
    "enriched": true
  }
}
```

**Response Fields**:
- **`response`** (string): ⭐ **THIS IS THE MAIN FIELD** - Contains the AI's answer text
- `provider` (string): The LLM provider used (e.g., "gemini", "openai")
- `model` (string): The specific model used (e.g., "gemini-2.0-flash", "gpt-4o-mini")
- `tokens` (number): Token count used
- **`context_hash`** (string): ⭐ **Optional performance feature**
  - Server-generated session ID for next request
  - **Ignore this if you prefer traditional approach**
  - **Use this only for conversations with 3+ exchanges**
  - Store it and send back in `context_hash` field of next request
  - See [Context Optimization Guide](CONTEXT_OPTIMIZATION.md) - completely optional!
- `product_context` (object, optional): Only present if product enrichment was applied
  - `uuid` (string): The product UUID
  - `enriched` (boolean): Whether the message was enriched with product context

### Error Response (HTTP 500)

```json
{
  "response": "Sorry... An error occurred."
}
```

**Error Fields**:
- `response` (string): Error message (still uses the `response` field for consistency)

---

## Important Notes for Frontend Integration

### The Response Text Field

**The chatbot response is always in the `response` field**, regardless of success or error status.

```javascript
// Frontend integration example
fetch('/chatbot', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`
  },
  body: JSON.stringify({
    message: userInput
  })
})
.then(res => res.json())
.then(data => {
  // Always read from data.response
  const botReply = data.response;
  displayMessage(botReply);
})
.catch(err => {
  console.error('Request failed:', err);
});
```

### Field Name Summary

- ✅ **Use**: `response` - This is the correct field name
- ❌ **Not**: `answer`, `text`, `reply`, `message`, or `output`

### Status Codes

- `200 OK` - Successful response
- `401 Unauthorized` - Missing or invalid API key
- `403 Forbidden` - Invalid authentication
- `500 Internal Server Error` - LLM processing error

---

## Complete Example

### Request
```bash
curl -X POST http://localhost:8004/chatbot \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "message": "What is Buildly?"
  }'
```

### Response
```json
{
  "response": "Buildly is a comprehensive platform for building, deploying, and managing modern applications. It provides workflow automation, API management, low-code development tools, and integration capabilities.",
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "tokens": 150
}
```

---

## Widget Integration Checklist

✅ Use `data.response` to get the bot's reply  
✅ Include `Authorization: Bearer <API_KEY>` header  
✅ Send user input in `message` field  
✅ Handle both 200 (success) and 500 (error) responses  
✅ Both use the same `response` field for the text  

---

## Response Field Name: `response`

**This is consistent across all scenarios:**
- ✅ Success: `response` contains the AI answer
- ✅ Error: `response` contains the error message

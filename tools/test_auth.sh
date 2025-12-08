#!/bin/bash
# Test script for API token authentication

echo "=========================================="
echo "Testing API Token Authentication"
echo "=========================================="

# Get the API token from .env
API_TOKEN=$(grep "^API_KEY=" .env | cut -d'=' -f2)

if [ -z "$API_TOKEN" ]; then
    echo "❌ No API_KEY found in .env file"
    exit 1
fi

echo "✅ API Token found: ${API_TOKEN:0:8}...${API_TOKEN: -4}"
echo ""

# Test 1: Get config endpoint (public)
echo "Test 1: GET /api/config (public endpoint)"
curl -s http://localhost:8004/api/config | jq '.' || echo "Failed"
echo ""

# Test 2: Chatbot endpoint WITH token
echo "Test 2: POST /chatbot WITH Authorization header"
curl -s -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello", "history": {"user": [], "bot": []}, "tokens": 0}' \
  | jq '.response' || echo "Failed"
echo ""

# Test 3: Chatbot endpoint WITHOUT token (should still work for web UI)
echo "Test 3: POST /chatbot WITHOUT Authorization header (public access)"
curl -s -X POST http://localhost:8004/chatbot \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hi", "history": {"user": [], "bot": []}, "tokens": 0}' \
  | jq '.response' || echo "Failed"
echo ""

# Test 4: Admin endpoint WITH token
echo "Test 4: GET /admin/tokens WITH Authorization header"
curl -s http://localhost:8004/admin/tokens \
  -H "Authorization: Bearer $API_TOKEN" \
  | jq '.env_token.token_preview' || echo "Failed"
echo ""

# Test 5: Admin endpoint WITHOUT token (should fail)
echo "Test 5: GET /admin/tokens WITHOUT Authorization header (should fail)"
curl -s http://localhost:8004/admin/tokens | jq '.' || echo "Expected failure"
echo ""

echo "=========================================="
echo "✅ Authentication tests complete"
echo "=========================================="

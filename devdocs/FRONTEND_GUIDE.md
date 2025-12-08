# Frontend Integration Guide - Simple API Key Auth

## Overview

BabbleBeaver now uses **simple API key authentication** instead of JWT tokens. The frontend just needs to send a static API key in the Authorization header.

## How It Works

1. **Admin logs in** with username/password → Gets the API key
2. **Frontend stores** the API key (localStorage/sessionStorage)
3. **All API requests** include the API key in the Authorization header

## Quick Start

### 1. Login to Get API Key

```javascript
// Login to get the API key
const response = await fetch('http://localhost:8004/admin/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'changeme123'
  })
});

const data = await response.json();
const apiKey = data.access_token; // This is your API key
```

### 2. Store the API Key

```javascript
// Store in localStorage or sessionStorage
localStorage.setItem('babblebeaver_api_key', apiKey);
```

### 3. Use the API Key for All Requests

```javascript
// Get the API key from storage
const apiKey = localStorage.getItem('babblebeaver_api_key');

// Send message to chatbot
const response = await fetch('http://localhost:8004/chatbot', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Hello, how can you help me?'
  })
});

const result = await response.json();
console.log(result.response);
```

## Complete React Example

```jsx
import React, { useState, useEffect } from 'react';

const BabbleBeaverChat = () => {
  const [apiKey, setApiKey] = useState(null);
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  // Check for stored API key on mount
  useEffect(() => {
    const storedKey = localStorage.getItem('babblebeaver_api_key');
    if (storedKey) {
      setApiKey(storedKey);
    }
  }, []);

  // Login function
  const login = async (username, password) => {
    try {
      const res = await fetch('http://localhost:8004/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await res.json();
      
      if (data.access_token) {
        setApiKey(data.access_token);
        localStorage.setItem('babblebeaver_api_key', data.access_token);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  // Send chat message
  const sendMessage = async () => {
    if (!apiKey) {
      alert('Please login first');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('http://localhost:8004/chatbot', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });

      const data = await res.json();
      setResponse(data.response);
    } catch (error) {
      console.error('Chat failed:', error);
      setResponse('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {!apiKey ? (
        <LoginForm onLogin={login} />
      ) : (
        <div>
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..."
          />
          <button onClick={sendMessage} disabled={loading}>
            {loading ? 'Sending...' : 'Send'}
          </button>
          {response && <div>Response: {response}</div>}
        </div>
      )}
    </div>
  );
};
```

## Complete Vanilla JavaScript Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>BabbleBeaver Chat</title>
</head>
<body>
    <div id="login-form">
        <h2>Login</h2>
        <input type="text" id="username" placeholder="Username" value="admin">
        <input type="password" id="password" placeholder="Password" value="changeme123">
        <button onclick="login()">Login</button>
    </div>

    <div id="chat-interface" style="display:none;">
        <h2>Chat</h2>
        <textarea id="message" placeholder="Type your message..."></textarea>
        <button onclick="sendMessage()">Send</button>
        <div id="response"></div>
        <button onclick="logout()">Logout</button>
    </div>

    <script>
        const API_URL = 'http://localhost:8004';
        let apiKey = localStorage.getItem('babblebeaver_api_key');

        // Check if already logged in
        if (apiKey) {
            showChat();
        }

        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch(`${API_URL}/admin/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (data.access_token) {
                    apiKey = data.access_token;
                    localStorage.setItem('babblebeaver_api_key', apiKey);
                    showChat();
                } else {
                    alert('Login failed: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Login error: ' + error.message);
            }
        }

        async function sendMessage() {
            const message = document.getElementById('message').value;

            try {
                const response = await fetch(`${API_URL}/chatbot`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${apiKey}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message })
                });

                const data = await response.json();
                document.getElementById('response').innerHTML = 
                    '<strong>Response:</strong> ' + data.response;
            } catch (error) {
                document.getElementById('response').innerHTML = 
                    '<strong>Error:</strong> ' + error.message;
            }
        }

        function logout() {
            localStorage.removeItem('babblebeaver_api_key');
            apiKey = null;
            showLogin();
        }

        function showChat() {
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('chat-interface').style.display = 'block';
        }

        function showLogin() {
            document.getElementById('login-form').style.display = 'block';
            document.getElementById('chat-interface').style.display = 'none';
        }
    </script>
</body>
</html>
```

## API Endpoints

### Login (Get API Key)
```
POST /admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "changeme123"
}

Response:
{
  "access_token": "aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck",
  "token_type": "bearer",
  "message": "Login successful"
}
```

### Send Chat Message
```
POST /chatbot
Authorization: Bearer aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck
Content-Type: application/json

{
  "message": "Hello, how can you help me?"
}

Response:
{
  "response": "AI response here...",
  "provider": "gemini",
  "model": "gemini-2.0-flash-exp"
}
```

### Get Suggested Prompts
```
GET /pre_user_prompt
Authorization: Bearer aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck

Response:
{
  "prompts": [
    "Tell me about Buildly",
    "What features do you offer?"
  ]
}
```

## Error Handling

```javascript
async function makeAuthenticatedRequest(url, options = {}) {
  const apiKey = localStorage.getItem('babblebeaver_api_key');
  
  if (!apiKey) {
    throw new Error('Not authenticated');
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    }
  });

  if (response.status === 401) {
    // API key is invalid
    localStorage.removeItem('babblebeaver_api_key');
    window.location.href = '/login';
    throw new Error('Authentication failed');
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || error.detail || 'Request failed');
  }

  return response.json();
}

// Usage
try {
  const data = await makeAuthenticatedRequest('http://localhost:8004/chatbot', {
    method: 'POST',
    body: JSON.stringify({ message: 'Hello' })
  });
  console.log(data.response);
} catch (error) {
  console.error('Error:', error.message);
}
```

## Security Notes

1. **Never expose the API key in client-side code** - Only store it after login
2. **Use HTTPS in production** - HTTP exposes the API key in transit
3. **Store in httpOnly cookies** (server-side) if possible for better security
4. **Clear on logout** - Always remove from localStorage when user logs out
5. **Handle expiration** - Currently keys don't expire, but handle 401 errors

## Current API Key (Development)

```
API_KEY=aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck
```

This is the current API key configured in `.env`. The frontend gets this by logging in with:
- Username: `admin`
- Password: `changeme123`

## Production Deployment

For production, generate a secure API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add it to your `.env` file:
```bash
API_KEY=YOUR_GENERATED_KEY_HERE
```

The key is **never stored in the database** - it's just an environment variable that's checked on every request.

# BabbleBeaver Developer Documentation

Welcome to the BabbleBeaver developer documentation. This guide provides comprehensive technical information for developers, contributors, and system administrators.

---

## 📚 Quick Start Guides

### For Frontend Developers
- **[API Reference](API.md)** - Complete API documentation with request/response formats
- **[Context Optimization](CONTEXT_OPTIMIZATION.md)** - Optional performance feature for multi-turn conversations
- **[URL Structure](URL_STRUCTURE.md)** - Application routes and page structure

### For Backend Developers
- **[Architecture Overview](#architecture)** - System design and components
- **[Buildly Agent](BUILDLY_AGENT.md)** - Agentic features and product data enrichment
- **[Context Optimization](CONTEXT_OPTIMIZATION.md)** - Performance optimization internals

### For Contributors
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute code
- **[Community Guidelines](COMMUNITY_GUIDELINES.md)** - Code of conduct and community values

### For System Administrators
- **[Context Optimization](CONTEXT_OPTIMIZATION.md)** - Configuration and monitoring
- **Production Deployment** - See main README.md

---

## 🎯 Documentation Index

### API & Integration
- **[API.md](API.md)** - Complete API reference
  - Chatbot endpoint
  - Authentication
  - Request/response formats
  - Error handling
  - Context hash feature (optional)

- **[FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)** - Frontend integration guide
  - Simple API key authentication
  - React examples
  - Context-aware integration
  - Best practices

### Performance & Optimization
- **[CONTEXT_OPTIMIZATION.md](CONTEXT_OPTIMIZATION.md)** - Performance guide
  - When to use context hashing (3+ message conversations)
  - Performance benchmarks (69-98% reduction)
  - Frontend integration examples (React, vanilla JS)
  - Backend architecture (LRU cache, compression, Redis)
  - Configuration and monitoring
  - Complete FAQ

- **[CONTEXT_AWARE_SYSTEM.md](CONTEXT_AWARE_SYSTEM.md)** - Context-aware AI system
  - Automatic context awareness
  - Product, user, and page context
  - Multi-use case adaptation
  - Frontend integration examples
  - System prompt enhancement

### Features & Modules
- **[BUILDLY_AGENT.md](BUILDLY_AGENT.md)** - Agentic capabilities
  - Automatic product data enrichment
  - UUID detection and API fetching
  - Integration guide
  - Performance benchmarks

### Application Structure
- **[URL_STRUCTURE.md](URL_STRUCTURE.md)** - Routes and pages
  - Public landing page (`/`)
  - Test chat interface (`/test`)
  - Admin dashboard (`/admin`)
  - Legacy chat page (`/chat`)

### Deployment & Infrastructure
- **[DATABASE_SETUP.md](DATABASE_SETUP.md)** - Database configuration
  - PostgreSQL setup
  - Google Cloud SQL
  - AWS RDS
  - Migration guide

- **[VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md)** - Vertex AI configuration
  - Google Cloud setup
  - Production deployment
  - Authentication

### Project Governance
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution workflow
  - Development setup
  - Pull request process
  - Code standards
  - Testing requirements

- **[COMMUNITY_GUIDELINES.md](COMMUNITY_GUIDELINES.md)** - Community expectations
  - Code of conduct
  - Values and principles
  - Reporting issues

- **[vision.md](vision.md)** - Project vision and roadmap
  - Long-term goals
  - Design philosophy
  - Future directions

---

## 🏗️ Architecture

BabbleBeaver is built on a modular architecture with the following key components:

### Core System
- **FastAPI Backend** - Handles API requests, routing, and LLM integration
- **Authentication** - Bearer token-based API key authentication
- **Context Management** - Optional performance optimization system

### LLM Integration
- **Multi-Provider Support** - OpenAI, Google (Gemini), Mistral, Anthropic, Cohere
- **Open-Source Providers** - Ollama, OpenRouter, HuggingFace
- **Configurable Models** - Easy integration via `model_config.ini`

### Agentic Features
- **Buildly Agent** - Intelligent product data enrichment
- **UUID Detection** - Automatic context gathering
- **Parallel API Calls** - Non-blocking async operations

### Performance Optimization
- **LRU Cache** - In-memory session storage (1000 sessions, 1hr TTL)
- **Compression** - zlib compression for contexts >1KB (60-80% reduction)
- **Context Hashing** - 95% payload reduction for conversations
- **Optional Redis** - Distributed caching for load-balanced deployments

### Frontend
- **Public Landing Page** - Information about BabbleBeaver and Buildly
- **Test Interface** - Simple API testing with suggested prompts
- **Admin Dashboard** - Full management interface
- **Chat Interface** - Legacy conversation UI

---

## 🚀 Key Features

### 1. Context Optimization (Optional)
**What:** Server-side session management that reduces payload sizes by 69-98% for multi-turn conversations.

**When to use:**
- ✅ Conversations with 3+ exchanges
- ❌ Single-shot questions (0% benefit)

**Performance:**
- 5 exchanges: **6.6x more efficient**
- 10 exchanges: **12.3x more efficient**
- 20 exchanges: **23.9x more efficient**

[Read full documentation →](CONTEXT_OPTIMIZATION.md)

### 2. Buildly Agent (Optional)
**What:** Agentic module that automatically enriches conversations with real-time Buildly Labs product data.

**How it works:**
1. Detects product UUIDs in messages
2. Fetches product info, features, releases in parallel
3. Enriches AI prompt with contextual data
4. Generates enhanced responses

**Enable in `.env`:**
```bash
BUILDLY_AGENT=true
BUILDLY_API_BASE_URL=https://labs-api.buildly.io
```

[Read full documentation →](BUILDLY_AGENT.md)

### 3. Multi-Provider LLM Support
Configure any LLM provider through `model_config/model_config.ini`:
- Add model configuration
- Specify provider, context length, API key
- Update completion function in `main.py`

See main README.md for detailed integration steps.

---

## 📖 Common Use Cases

### Frontend: Simple Chat Implementation
```javascript
const chat = new SimpleChatbot('http://localhost:8004', 'API_KEY');
await chat.sendMessage('Hello');
await chat.sendMessage('Tell me more');
```
[See full example →](CONTEXT_OPTIMIZATION.md#frontend-integration)

### Backend: Enable Buildly Agent
```bash
# .env file
BUILDLY_AGENT=true
BUILDLY_API_BASE_URL=https://labs-api.buildly.io
```
[See full documentation →](BUILDLY_AGENT.md)

### DevOps: Monitor Context Cache
```bash
curl http://localhost:8004/admin/context/stats \
  -H "Authorization: Bearer YOUR_API_KEY"
```
[See monitoring guide →](CONTEXT_OPTIMIZATION.md#monitoring)

---

## 🔧 Configuration

### Environment Variables

**Required:**
```bash
# API Keys (at least one provider)
GOOGLE_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key
```

**Optional - Context Management:**
```bash
CONTEXT_CACHE_SIZE=1000        # Max sessions in memory
CONTEXT_CACHE_TTL=3600         # Session expiry (seconds)
USE_REDIS=false                # Enable Redis for distributed systems
REDIS_URL=redis://localhost:6379/0
```

**Optional - Buildly Agent:**
```bash
BUILDLY_AGENT=true
BUILDLY_API_BASE_URL=https://labs-api.buildly.io
```

See `example.env` for complete configuration template.

---

## 🧪 Testing

### Test API Endpoint
```bash
curl -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, BabbleBeaver!"}'
```

### Test Context Hashing
```bash
# Get hash from first response
HASH=$(curl -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}' | jq -r '.context_hash')

# Use hash in second request
curl -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Tell me more\", \"context_hash\":\"$HASH\"}"
```

### Test Buildly Agent
```bash
curl -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me about product_uuid: YOUR_UUID"}'
```

---

## 📝 API Quick Reference

### POST /chatbot

**Request:**
```json
{
  "message": "Your question",
  "history": {"user": [], "bot": []},  // Optional (omit if using context_hash)
  "context_hash": "abc123",             // Optional (server-provided)
  "product_uuid": "uuid-here",          // Optional
  "tokens": 150                         // Optional
}
```

**Response:**
```json
{
  "response": "AI answer",
  "context_hash": "abc123",  // Use this in next request
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "tokens": 150
}
```

[Full API documentation →](API.md)

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Read the guidelines:** [CONTRIBUTING.md](CONTRIBUTING.md)
2. **Understand the community:** [COMMUNITY_GUIDELINES.md](COMMUNITY_GUIDELINES.md)
3. **Check the vision:** [vision.md](vision.md)
4. **Fork and submit PRs** on GitHub

---

## 📚 Additional Resources

### External Documentation
- **Buildly Labs API:** https://labs-api.buildly.io/docs/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Gemini API:** https://ai.google.dev/docs
- **OpenAI API:** https://platform.openai.com/docs

### Repository Structure
```
babblebeaver/
├── devdocs/              # This documentation
├── modules/
│   └── buildly_labs/     # Buildly Agent module
├── model_config/         # LLM configuration
├── templates/            # Frontend templates
├── static/               # CSS/JS assets
├── main.py               # FastAPI application
├── context_manager.py    # Context optimization
├── requirements.txt      # Python dependencies
└── docker-compose.yml    # Docker setup
```

---

## 📞 Support

- **GitHub Issues:** Report bugs and request features
- **Community:** See [COMMUNITY_GUIDELINES.md](COMMUNITY_GUIDELINES.md)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

BabbleBeaver is GPL-licensed. See the [LICENSE](../LICENSE) file for details.


# Buildly Labs Agent - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BabbleBeaver System                             │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      FastAPI Application (main.py)                  │ │
│  │                                                                     │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │              POST /chatbot Endpoint                          │ │ │
│  │  │                                                              │ │ │
│  │  │  1. Receive user message + optional product_uuid            │ │ │
│  │  │  2. Check if BUILDLY_AGENT_AVAILABLE                        │ │ │
│  │  │  3. Call enrich_user_message()  ┌──────────────────────┐   │ │ │
│  │  │                                  │                      │   │ │ │
│  │  │                                  ▼                      │   │ │ │
│  │  │  ┌────────────────────────────────────────────────┐    │   │ │ │
│  │  │  │   Buildly Labs Agent Module                    │    │   │ │ │
│  │  │  │   (modules/buildly-labs/buildly_agent.py)      │    │   │ │ │
│  │  │  │                                                 │    │   │ │ │
│  │  │  │  ┌──────────────────────────────────────────┐  │    │   │ │ │
│  │  │  │  │ Step 1: Extract/Detect product_uuid      │  │    │   │ │ │
│  │  │  │  │ - Regex pattern matching                 │  │    │   │ │ │
│  │  │  │  │ - Or use explicit parameter              │  │    │   │ │ │
│  │  │  │  └──────────────────────────────────────────┘  │    │   │ │ │
│  │  │  │                    ▼                            │    │   │ │ │
│  │  │  │  ┌──────────────────────────────────────────┐  │    │   │ │ │
│  │  │  │  │ Step 2: Parallel Async API Calls         │  │    │   │ │ │
│  │  │  │  │                                           │  │    │   │ │ │
│  │  │  │  │  ┌─────────────────────────────────┐     │  │    │   │ │ │
│  │  │  │  │  │ asyncio.gather() - 5s timeout   │     │  │    │   │ │ │
│  │  │  │  │  │                                  │     │  │    │   │ │ │
│  │  │  │  │  │  ┌──────────────────────────┐   │     │  │    │   │ │ │
│  │  │  │  │  │  │ GET /products/{uuid}     │   │     │  │    │   │ │ │
│  │  │  │  │  │  └──────────────────────────┘   │     │  │    │   │ │ │
│  │  │  │  │  │           ║                      │     │  │    │   │ │ │
│  │  │  │  │  │  ┌────────║──────────────────┐  │     │  │    │   │ │ │
│  │  │  │  │  │  │ GET /products/{uuid}/    │  │     │  │    │   │ │ │
│  │  │  │  │  │  │     features              │  │     │  │    │   │ │ │
│  │  │  │  │  │  └──────────────────────────┘  │     │  │    │   │ │ │
│  │  │  │  │  │           ║                      │     │  │    │   │ │ │
│  │  │  │  │  │  ┌────────║──────────────────┐  │     │  │    │   │ │ │
│  │  │  │  │  │  │ GET /products/{uuid}/    │  │     │  │    │   │ │ │
│  │  │  │  │  │  │     releases              │  │     │  │    │   │ │ │
│  │  │  │  │  │  └──────────────────────────┘  │     │  │    │   │ │ │
│  │  │  │  │  └─────────────────────────────────┘     │  │    │   │ │ │
│  │  │  │  └──────────────────────────────────────────┘  │    │   │ │ │
│  │  │  │                    ▼                            │    │   │ │ │
│  │  │  │  ┌──────────────────────────────────────────┐  │    │   │ │ │
│  │  │  │  │ Step 3: Format Context                   │  │    │   │ │ │
│  │  │  │  │ - Product info                           │  │    │   │ │ │
│  │  │  │  │ - Features list                          │  │    │   │ │ │
│  │  │  │  │ - Releases/versions                      │  │    │   │ │ │
│  │  │  │  └──────────────────────────────────────────┘  │    │   │ │ │
│  │  │  │                    ▼                            │    │   │ │ │
│  │  │  │  ┌──────────────────────────────────────────┐  │    │   │ │ │
│  │  │  │  │ Step 4: Enrich User Message              │  │    │   │ │ │
│  │  │  │  │ Original + Context = Enriched Prompt     │  │    │   │ │ │
│  │  │  │  └──────────────────────────────────────────┘  │    │   │ │ │
│  │  │  │                    ▼                            │    │   │ │ │
│  │  │  │  Return: (enriched_message, product_context)   │    │   │ │ │
│  │  │  └────────────────────────────────────────────────┘    │   │ │ │
│  │  │                                  │                      │   │ │ │
│  │  │  4. Use enriched_message for AI ◄──────────────────────┘   │ │ │
│  │  │  5. Process with AIConfigurator                           │ │ │
│  │  │  6. Return response + product_context metadata            │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────── │ │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────┐
        │    Buildly Labs API                       │
        │    (labs-api.buildly.io)                  │
        │                                           │
        │  ┌─────────────────────────────────────┐ │
        │  │ /products/{uuid}                    │ │
        │  │ Returns: name, description, version │ │
        │  └─────────────────────────────────────┘ │
        │  ┌─────────────────────────────────────┐ │
        │  │ /products/{uuid}/features           │ │
        │  │ Returns: feature list with details  │ │
        │  └─────────────────────────────────────┘ │
        │  ┌─────────────────────────────────────┐ │
        │  │ /products/{uuid}/releases           │ │
        │  │ Returns: version history, notes     │ │
        │  └─────────────────────────────────────┘ │
        └───────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════
                              DATA FLOW
═══════════════════════════════════════════════════════════════════════════

Input Message:
┌────────────────────────────────────────────────────────────────────────┐
│ "What features does product_uuid: abc-123 have?"                      │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
Enriched Message:
┌────────────────────────────────────────────────────────────────────────┐
│ "What features does product_uuid: abc-123 have?"                      │
│                                                                        │
│ --- BUILDLY LABS PRODUCT CONTEXT ---                                  │
│ Product Information:                                                   │
│   - name: BabbleBeaver                                                 │
│   - version: 2.0.1                                                     │
│   - description: AI-powered chatbot platform                           │
│                                                                        │
│ Product Features:                                                      │
│   1. Multi-model Support                                               │
│      Supports OpenAI, Gemini, and custom models                        │
│   2. Conversation History                                              │
│      Token-aware history management                                    │
│                                                                        │
│ Product Releases:                                                      │
│   1. Version 2.0.1                                                     │
│      Released: 2025-01-15                                              │
│      Notes: Bug fixes and performance improvements                     │
│ --- END PRODUCT CONTEXT ---                                            │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
AI Processing (Gemini/OpenAI)
                                │
                                ▼
Enhanced Response:
┌────────────────────────────────────────────────────────────────────────┐
│ "BabbleBeaver version 2.0.1 includes several key features:            │
│  1. Multi-model Support - You can use OpenAI, Gemini, or custom       │
│     models seamlessly                                                  │
│  2. Conversation History - The system manages conversation context     │
│     with token-aware history tracking                                  │
│                                                                        │
│ The latest release (2.0.1) from January 15, 2025 includes bug fixes   │
│ and performance improvements."                                         │
└────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════
                         PERFORMANCE TIMELINE
═══════════════════════════════════════════════════════════════════════════

Without Agent:
├─ 0ms      User message received
├─ 10ms     Message processed
├─ 2000ms   AI generates response
└─ 2010ms   Response returned
            Total: ~2 seconds

With Agent (Parallel):
├─ 0ms      User message received
├─ 10ms     UUID detected
├─ 10ms     Start 3 parallel API calls
│           ├─ GET /products/{uuid}
│           ├─ GET /products/{uuid}/features
│           └─ GET /products/{uuid}/releases
├─ 5000ms   All API calls complete (timeout: 5s)
├─ 5100ms   Context formatted and prompt enriched
├─ 7000ms   AI generates response (parallel with API calls)
└─ 7100ms   Response returned
            Total: ~7 seconds (not 15!)


═══════════════════════════════════════════════════════════════════════════
                         MODULE STRUCTURE
═══════════════════════════════════════════════════════════════════════════

modules/
└── buildly-labs/
    ├── __init__.py              # Public API exports
    ├── buildly_agent.py         # Core agent implementation
    │   ├── BuildlyAgent         # Main agent class
    │   │   ├── __init__()
    │   │   ├── get_product_info()
    │   │   ├── get_product_features()
    │   │   ├── get_product_releases()
    │   │   ├── gather_product_context()
    │   │   ├── format_context_for_prompt()
    │   │   ├── enrich_prompt()
    │   │   └── extract_product_uuid()
    │   ├── get_agent()          # Singleton getter
    │   └── enrich_user_message()# Convenience function
    ├── test_agent.py            # Test suite
    ├── README.md                # Full documentation
    ├── EXAMPLES.md              # Usage examples
    └── QUICKSTART.md            # Quick reference


═══════════════════════════════════════════════════════════════════════════
                         ERROR HANDLING FLOW
═══════════════════════════════════════════════════════════════════════════

User Message
     │
     ├─ BUILDLY_AGENT=false ──────────────┐
     │                                     │
     ├─ Module import fails ──────────────┤
     │                                     │
     ├─ No product_uuid found ────────────┤
     │                                     │
     ├─ API timeout (>5s) ────────────────┤
     │                                     │
     ├─ HTTP error (404, 500, etc) ───────┤
     │                                     │
     ├─ Invalid JSON response ────────────┤
     │                                     │
     └─ Network error ────────────────────┤
                                          │
                                          ▼
                              ┌──────────────────────┐
                              │ Graceful Degradation │
                              │                      │
                              │ - Log warning        │
                              │ - Use original msg   │
                              │ - Continue normally  │
                              │ - No user error      │
                              └──────────────────────┘
```

**Legend:**
- `│`, `└`, `├`, `─`, `▼`: Flow direction
- `║`: Parallel execution
- `┌`, `┐`, `└`, `┘`: Box borders
- `═`: Section dividers

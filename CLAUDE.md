# BabbleBeaver

Open-source, privacy-focused conversational AI platform built with FastAPI.

## Tech Stack
- **Backend:** FastAPI + Uvicorn (Python 3.9+)
- **Database:** SQLite (dev) / PostgreSQL (prod) via SQLAlchemy ORM
- **LLM Providers:** Google Gemini/Vertex AI (primary, fine-tuned), OpenAI, Ollama, OpenRouter, HuggingFace, Anthropic, Cohere
- **Deployment:** Docker, GitHub Actions CI/CD → Google Artifact Registry → Kubernetes / DigitalOcean

## Running Locally
```bash
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Access at http://localhost:8000 | API docs at http://localhost:8000/docs

## Project Structure
- `main.py` — FastAPI app entry point
- `ai_configurator.py` — LLM provider orchestration
- `llm_manager.py` — Multi-provider fallback manager
- `database.py` — SQLAlchemy ORM models (incl. `DailyScore` snapshots)
- `context_manager.py` — Conversation context handling
- `user_context.py` — Fetches user health profile/biometrics from user_service
- `scoring.py` — Deterministic Kai MAI scoring engine (implements SCORING.md)
- `daily_scores.py` — Persists/retrieves daily score snapshots (drift baselines)
- `SCORING.md` — Authoritative scoring rules (18 rules + meal-level mode)
- `cost_estimator.py` — Multi-provider cost comparison
- `model_config/` — Model definitions (model_config.ini)
- `templates/` — HTML UI (chat, admin)
- `static/` — Frontend assets
- `modules/` — Feature modules (buildly-collect, digitalocean, gemini)
- `tools/` — Test & migration utilities
- `ops/` — Operations (PID management)

## Key Commands
```bash
# Database migration
python3 tools/migrate_database.py --dry-run
python3 tools/migrate_database.py

# Tests
python3 tools/test_database.py
python3 tools/test_context_aware.py
python3 tools/test_scoring.py   # scoring engine unit tests (pure, no network)
```

## Kai Scoring System
- Rules live in `SCORING.md` and are **authoritative** — `scoring.py` implements
  them exactly; never let the LLM compute the math.
- Foundation scores (Rules 1–10) feed composites (Rules 11–18); CGM scores are
  gated on connection + consent. Missing inputs flag a score incomplete (never
  estimated).
- `level="meal"` mode scales daily targets by `meal_divisor` (default 3) for
  per-dish ranking; `level="daily"` (default) is for user adherence.
- `/chatbot` computes scores from user_service context, upserts a per-day
  `DailyScore` row, and injects a `KAI HEALTH SCORES` block into Kai's prompt.

## Environment
- Config via `.env` (API keys, GCP project settings, database URL)
- Model config via `model_config/model_config.ini`
- Primary fine-tuned model: `kai_fine_2_5_v2` on Vertex AI

## CI/CD
- `dev` branch → dev-build.yml → dev image
- `prod` branch → prod-build.yml → prod image → Artifact Registry → K8s manifest update

## Important Notes
- Never commit `.env` or credential JSON files
- CORS domains configured via `CORS_ALLOWED_DOMAINS` env var
- Database auto-switches between SQLite/PostgreSQL based on `DATABASE_URL` presence

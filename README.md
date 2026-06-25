# WOHANA News Agent — Backend

FastAPI service that collects world news from Google News (per-country editions),
extracts article content, and uses an LLM (Groq) to summarise, categorise, detect
sentiment, identify the country, and extract reported impact counts. Aggregated
analytics are exposed for the dashboard.

## Stack

- FastAPI + Uvicorn
- SQLAlchemy 2 (async) + Alembic + PostgreSQL (`asyncpg`)
- APScheduler (periodic collection)
- Groq LLM for processing
- feedparser + trafilatura / newspaper4k for collection & extraction

## Setup

```bash
# 1. Install deps (pip)
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
# (or, with uv:  uv sync)

# 2. Configure environment
cp .env.example .env
#   edit .env — set DATABASE_URL, GROQ_API_KEY, SECRET_KEY, ADMIN_* …

# 3. Create the schema
alembic upgrade head

# 4. Seed an admin user and the default keyword set
python seed_admin.py
python seed_keywords.py

# 5. Run
uvicorn main:app --host 0.0.0.0 --port 8001
```

API docs: `http://localhost:8001/api/docs`

## Configuration

All settings come from environment variables (see `.env.example`). In production,
provide them via the host/container environment rather than a committed `.env`.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async Postgres URL (`postgresql+asyncpg://…`) |
| `GROQ_API_KEY` / `GROQ_MODEL` | LLM credentials / model |
| `SECRET_KEY` | JWT signing secret |
| `NEWS_FETCH_INTERVAL_HOURS` | Scheduler interval (`0.25` = 15 min) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seeded admin credentials |

## News collection

Articles are fetched per country from Google News editions defined in
`app/collectors/countries.py`. The monitored set defaults to all configured
countries and can be changed at runtime via the admin API (`/api/admin/countries`).

## Tests

```bash
pytest
```

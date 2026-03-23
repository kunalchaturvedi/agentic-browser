# Agentic Browser

Agentic Browser is a local-first project that turns search-style queries into rendered webpages instead of chat-style answer blobs.

The current scaffold targets `Python 3.9+` for local development compatibility.

## Phase 1 status

Phase 1 provides:

- project scaffolding
- environment-based configuration
- FastAPI application bootstrap
- root endpoint
- health endpoint

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
copy .env.example .env
python run.py
```

Then open `http://127.0.0.1:8000/health`.

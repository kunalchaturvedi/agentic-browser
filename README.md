# Agentic Browser

Agentic Browser is a local-first project that turns search-style queries into rendered webpages instead of chat-style answer blobs.

The current scaffold targets `Python 3.9+` for local development compatibility.

## Current project status

The repository currently includes:

- requirements and design documents in `docs\`
- a Phase 1 FastAPI scaffold under `src\agentic_browser\`
- a local health check endpoint and smoke tests
- a GitHub branch and PR for the initial foundation work

See `CHANGELOG.md` for milestone history.

## Phase 1 status

Phase 1 provides:

- project scaffolding
- environment-based configuration
- FastAPI application bootstrap
- root endpoint
- health endpoint
- basic test coverage for startup and health responses

## Documentation

- `docs\requirements.md` captures goals, scope, MVP boundaries, and constraints.
- `docs\design.md` captures architecture, component boundaries, and implementation direction.
- `CHANGELOG.md` tracks milestones and notable repository updates.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
copy .env.example .env
python run.py
```

Then open `http://127.0.0.1:8000/health`.

Run tests with:

```bash
pytest
```

## Current next step

The next implementation milestone is Phase 2: search integration and result normalization.

# Agentic Browser

Agentic Browser is a local-first project that turns user prompts into navigable webpages instead of chat-style answer blobs.

The long-term goal is a browser-like experience where the system can decide when to search, gather evidence from multiple sources, synthesize structured content, and render the result as a page the user can keep exploring.

## Current Status

The current branch includes the Tavily-backed search slice, LangGraph agent workflow, initial HTML rendering, navigation continuity, the first LLM planner slice, and the first LLM-backed synthesis slice via Azure AI Foundry; see `docs\implementation_plan.md` and `CHANGELOG.md` for details.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
copy .env.example .env
python run.py
```

Then open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/search?q=agentic%20browser&limit=3`

You can also exercise:

- `POST http://127.0.0.1:8000/agent` for JSON output
- `POST http://127.0.0.1:8000/agent/render` for HTML output
- `GET http://127.0.0.1:8000/agent/pages/{session_id}/{page_id}` for stored generated pages
- `GET http://127.0.0.1:8000/agent/follow-up?...` for navigation-aware follow-up pages

Run tests with:

```bash
pytest
```

Check Azure AI Foundry connectivity with:

```bash
python scripts\check_azure_foundry_connection.py
```

Fill the Azure values in your local `.env` with your own resource endpoint, deployment name, API version, and key before running the check.

## Project Documents

- `docs\requirements.md` — product goals, scope, constraints, and success criteria
- `docs\design.md` — architecture, component boundaries, and technical rationale
- `docs\implementation_plan.md` — current progress, implementation phases, and next milestones
- `CHANGELOG.md` — notable repository changes

## Development Notes

- Python baseline: `3.9+`
- configuration is environment-driven
- current entry point: `python run.py`
- internal generated-page links use `APP_BASE_URL` and default to `http://127.0.0.1:8000`
- search provider: Tavily
- optional planner and synthesis model: `GPT-4.1 mini` via Azure AI Foundry
- planner timeout is controlled by `AZURE_OPENAI_TIMEOUT_SECONDS`
- synthesis timeout is controlled by `AZURE_OPENAI_SYNTHESIS_TIMEOUT_SECONDS`

## Why This Project Exists

Many AI systems make information faster to consume, but they often flatten rich source material into text-heavy answers. This project explores a different interface: use AI for orchestration and synthesis, but present the result as a webpage-like experience that feels closer to browsing than chatting.

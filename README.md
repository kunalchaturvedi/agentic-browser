# Agentic Browser

Agentic Browser is a local-first project that turns user prompts into navigable webpages instead of chat-style answer blobs.

The long-term goal is a browser-like experience where the system can decide when to search, gather evidence from multiple sources, synthesize structured content, and render the result as a page the user can keep exploring.

## Current Status

The current branch includes the Tavily-backed search slice, LangGraph agent workflow, structured page synthesis, and an initial HTML rendering path; see `docs\implementation_plan.md` and `CHANGELOG.md` for details.

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

Run tests with:

```bash
pytest
```

## Project Documents

- `docs\requirements.md` — product goals, scope, constraints, and success criteria
- `docs\design.md` — architecture, component boundaries, and technical rationale
- `docs\implementation_plan.md` — current progress, implementation phases, and next milestones
- `CHANGELOG.md` — notable repository changes

## Development Notes

- Python baseline: `3.9+`
- configuration is environment-driven
- current entry point: `python run.py`
- search provider: Tavily

## Why This Project Exists

Many AI systems make information faster to consume, but they often flatten rich source material into text-heavy answers. This project explores a different interface: use AI for orchestration and synthesis, but present the result as a webpage-like experience that feels closer to browsing than chatting.

# Agentic Browser

Agentic Browser is a local-first project that turns user prompts into rendered webpages instead of chat-style answer blobs.

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
- `docs\implementaiton_plan.md` captures the long-term phase roadmap and LangGraph build direction.
- `docs\addmermaid.js` can render Mermaid code blocks in a browser-based docs shell.
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

## Current implementation

The project now includes an early search integration slice:

- `GET /search?q=...&limit=...`
- normalized search request and response models
- a Tavily-backed search service layer
- tests for route behavior and normalization

The project now also includes an initial Phase 3 LangGraph slice:

- `POST /agent`
- a deterministic planner
- LangGraph state and workflow wiring
- graph nodes for search, source selection, fetch, and extraction
- terminal-visible request and workflow logging
- tests for planner behavior, graph execution, and route behavior
- Mermaid diagrams documenting the high-level architecture and current code flow

## Current next step

The next implementation milestone is Phase 4: structured page synthesis from the evidence gathered by the LangGraph workflow.

For the hobby-project search provider, the recommended choice is **Tavily**, with **Serper.dev** as the simplest fallback if we only want a URL/snippet search API.

## Roadmap

### Phase 1: Foundation

- project scaffold
- FastAPI app
- config and environment setup
- health endpoint
- smoke tests

Status: complete

### Phase 2: Search Slice

- normalized search models
- search service
- `GET /search`
- tests for normalization and route behavior

Status: complete as an initial slice

### Phase 3: LangGraph Agent Loop

- LangGraph state definition
- planner node
- search/fetch/extract nodes
- evidence assembly
- graph transition tests

Status: initial slice implemented

### Phase 4: Structured Page Synthesis

- synthesis node outputs structured page data
- page schema for title, sections, links, citations, media, and theme
- validation of structured outputs

Status: planned

### Phase 5: Rendering Engine

- render structured page data into HTML
- support cards, sections, citations, media, and theme
- keep the output webpage-like instead of chat-like

Status: planned

### Phase 6: Context-Aware Navigation

- feed clicks and follow-up prompts back into the graph
- preserve page and evidence context
- support drill-down navigation

Status: planned

### Phase 7: Asset and Style Refinement

- improve image selection
- improve style extraction from sources
- refine page theming and layout quality

Status: planned

### Phase 8: Evaluation and Optimization

- quality evaluation
- latency tuning
- caching
- cost controls
- robustness improvements

Status: planned

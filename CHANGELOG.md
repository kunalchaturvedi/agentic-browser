# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- initial normalized search models for query and result payloads
- initial `GET /search` route contract
- Tavily-backed search service for retrieval
- tests for search route behavior and payload normalization
- initial LangGraph agent package and state model
- deterministic planner and constrained agent workflow
- initial `POST /agent` route
- graph nodes for search, source selection, fetch, extraction, and synthesis
- tests for planner behavior, graph execution, agent route behavior, and page-model validation
- terminal-visible INFO logging for request handling, planner routing, and Tavily calls
- Mermaid architecture and code-flow diagrams in the design and implementation docs
- `docs\addmermaid.js` helper for rendering Mermaid code blocks in a browser-based docs shell
- `docs\implementation_plan.md` as the canonical implementation-progress document
- structured page models for synthesized output
- synthesis node that converts extracted evidence into page data
- `/agent` responses that now include synthesized page data
- deterministic HTML renderer for synthesized page output
- `POST /agent/render` HTML route
- tests for rendering output and rendered route behavior
- in-memory navigation store for page and session continuity
- `GET /agent/pages/{session_id}/{page_id}` route for stored generated pages
- `GET /agent/follow-up` route for navigation-aware follow-up rendering
- page and session identifiers in rendered/generated responses
- tests for navigation continuity and stored page behavior

### Changed

- restructured project documentation so `README.md` stays public-facing while `docs\design.md` and `docs\implementation_plan.md` hold architecture and planning detail
- updated docs to reflect that the current codebase now includes the Tavily search slice, LangGraph workflow, structured synthesis, initial rendering, and initial navigation continuity

### Planned

- richer render strategies beyond the deterministic renderer
- browser-like UX refinement across navigation, rendering quality, and robustness

## [0.1.0] - Initial foundation

### Added

- project requirements document in `docs\requirements.md`
- system design document in `docs\design.md`
- FastAPI application scaffold under `src\agentic_browser\`
- environment-based settings and `.env.example`
- `GET /` and `GET /health` endpoints
- smoke tests for the current API surface
- `run.py`, `pyproject.toml`, `requirements.txt`, and `README.md`

### Repository

- initialized Git in the project directory
- created and pushed branch `phase1-foundation`
- opened pull request `#1` into `main`
- configured repo-local Git and credential settings for the personal GitHub account while leaving global Git settings unchanged

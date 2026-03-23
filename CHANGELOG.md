# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- initial normalized search models for query and result payloads
- initial `GET /search` route contract
- initial search service for Tavily-backed retrieval
- tests for search route behavior and payload normalization
- initial LangGraph agent package and state model
- initial deterministic planner and constrained agent workflow
- initial `POST /agent` route
- graph nodes for search, source selection, fetch, and extraction
- tests for planner behavior, graph execution, and agent route behavior
- terminal-visible INFO logging for request handling, planner routing, and Tavily calls
- Mermaid architecture and code-flow diagrams in the design and implementation docs
- `docs\addmermaid.js` helper for rendering Mermaid code blocks in a browser-based docs shell

### Planned

- Phase 4 structured page synthesis
- structured render plan generation
- HTML rendering from synthesized page data

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

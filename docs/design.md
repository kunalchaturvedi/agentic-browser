# Agentic Browser Design

## Purpose

This document describes the initial system design for the Agentic Browser MVP and the technical choices behind Phase 1 scaffolding.

## Architecture Summary

The application is a server-rendered web app with a modular backend. The backend accepts user queries, orchestrates search and synthesis, and renders structured results into HTML templates.

## High-Level Flow

1. User submits a query from the browser UI.
2. FastAPI route receives the request.
3. Search service fetches relevant results.
4. Scraper service retrieves content from selected URLs.
5. Synthesizer service prepares a prompt and requests structured output from the LLM.
6. Renderer converts structured data into HTML.
7. Generated links embed enough metadata to continue the navigation journey.

## Major Components

### Web Application Layer

- `FastAPI` handles HTTP routing and lifecycle concerns.
- Route modules remain thin and delegate to services.

### Configuration Layer

- Centralized settings are loaded from environment variables.
- Runtime configuration includes host, port, debug mode, app name, and future API credentials.

### Search Service

- Responsible for provider integration, request shaping, result normalization, and provider-specific error handling.
- Initial provider target: Bing Search API.

### Scraper Service

- Responsible for downloading page content and extracting meaningful text.
- Initial approach: `httpx` and `BeautifulSoup4`.
- Optional fallback: browser automation with Playwright for difficult pages.

### Synthesis Service

- Responsible for prompt construction, source aggregation, and calling the LLM.
- The LLM must return structured content rather than raw HTML.

### Rendering Layer

- Template-based rendering converts a trusted internal page model into consistent HTML.
- This is preferred over directly rendering arbitrary LLM HTML in the MVP.

### Context Management

- A lightweight context object captures query history and navigation state.
- Generated hyperlinks should reference context identifiers or encoded navigation intents.

## Initial Package Layout

```text
agentic-browser/
├── docs/
├── src/
│   └── agentic_browser/
│       ├── routes/
│       ├── services/
│       ├── rendering/
│       └── models/
├── tests/
├── .env.example
├── pyproject.toml
├── requirements.txt
└── run.py
```

## Phase 1 Design Decisions

### 1. `src` Layout

A `src` layout helps avoid accidental imports from the repository root and is a solid baseline for packaging and tests.

### 2. Simple FastAPI Entry Point

Phase 1 keeps the app boot path minimal:

- `agentic_browser.config` loads settings.
- `agentic_browser.main` creates the FastAPI app.
- `agentic_browser.routes.health` exposes a health endpoint.

### 3. Pydantic Settings

Environment-backed settings provide typed configuration and keep secrets out of source control.

### 4. Template-First Rendering Strategy

Even though rendering is not implemented in Phase 1, the design assumes structured data rendered by templates. This reduces prompt risk, improves consistency, and keeps styling under application control.

## API Surface for Phase 1

### `GET /`

Returns a small JSON payload confirming the application is running and identifying the project.

### `GET /health`

Returns a lightweight health response suitable for local checks and future readiness probes.

## Future Routes

- `GET /search`
- `POST /search`
- `GET /page/{page_id}`
- `POST /navigate`

These routes are deferred until search, synthesis, and rendering layers are implemented.

## Data Model Direction

The initial internal page model should eventually support:

- query metadata
- page title
- hero summary
- ordered sections
- source citations
- related links with navigation intent

## Error Handling Strategy

- Configuration errors should fail fast at startup.
- External service errors should be surfaced explicitly and mapped to useful HTTP responses.
- The MVP should avoid broad catch-and-ignore patterns.

## Security and Safety Notes

- Secrets must come from environment variables.
- Rendered HTML should come from trusted templates and escaped content.
- External content extraction should be sanitized before use.

## Local Development Plan

- Install dependencies.
- Copy `.env.example` to `.env`.
- Run `python run.py`.
- Verify `GET /health`.

## Runtime Baseline

Phase 1 targets Python 3.9+ so the local scaffold remains compatible with the currently available interpreter while keeping the codebase ready for newer Python versions later.

## Open Design Items

- Session storage format for navigation context.
- Search result selection strategy before synthesis.
- Structured output schema for the synthesizer.
- Template composition for synthesized pages.

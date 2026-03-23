# Agentic Browser Design

## Purpose

This document describes the current system architecture, target architecture, and technical rationale behind Agentic Browser.

It focuses on **how the system is structured** and **why the project is organized this way**.

For implementation phases and milestone tracking, see `docs\implementation_plan.md`.

## Current Implementation Boundary

The current codebase includes:

- FastAPI application bootstrap
- environment-backed configuration
- `GET /`, `GET /health`, `GET /search`, and `POST /agent`
- Tavily-backed search integration
- normalized search and agent response models
- an initial LangGraph workflow with planner, search, fetch, and extraction nodes
- terminal-visible request and workflow logging
- tests for health, search, planner behavior, and agent workflow execution

Structured page synthesis, final HTML rendering, and context-aware navigation are still planned rather than implemented.

## System Summary

Agentic Browser is designed as a local-first web application that accepts a user prompt, decides whether retrieval is needed, gathers evidence from the web, synthesizes structured content, and renders the result as a webpage-like experience.

The main architectural split is:

- a web application boundary that handles requests and responses
- an internal agent workflow that plans, retrieves, synthesizes, and renders

## Mermaid Diagrams

If these docs are rendered in a browser-based docs shell, `docs\addmermaid.js` can turn Mermaid code blocks into diagrams automatically.

### High-Level System Diagram

```mermaid
flowchart TD
    User[User or Browser UI]
    FastAPI[FastAPI app\nmain.py + routes]
    AgentRoute[POST /agent\nroutes/agent.py]
    SearchRoute[GET /search\nroutes/search.py]
    Workflow[AgentWorkflow\nagent/graph.py]
    Planner[Planner\nagent/planner.py]
    SearchService[SearchService\nservices/search.py]
    Tavily[Tavily Search API]
    Fetcher[PageFetcher\nnodes/fetch.py]
    Extractor[Extractor + Finalizer\nnodes/extract.py]
    Synthesize[Synthesis node\nplanned]
    Render[Rendering layer\nplanned]
    Health[GET /health]

    User --> FastAPI
    FastAPI --> AgentRoute
    FastAPI --> SearchRoute
    FastAPI --> Health
    AgentRoute --> Workflow
    Workflow --> Planner
    Workflow --> SearchService
    SearchRoute --> SearchService
    SearchService --> Tavily
    Workflow --> Fetcher
    Workflow --> Extractor
    Extractor --> Synthesize
    Synthesize --> Render
    Render --> User
```

### Current Code Flow

```mermaid
sequenceDiagram
    participant U as Client
    participant R as routes/agent.py
    participant G as agent/graph.py
    participant P as planner.py
    participant S as nodes/search.py
    participant SS as services/search.py
    participant T as Tavily
    participant F as nodes/fetch.py
    participant E as nodes/extract.py

    U->>R: POST /agent
    R->>G: workflow.run(request)
    G->>P: planner.plan(request)
    P-->>G: decision + search_queries + source_limit

    alt answer_from_context
        G->>E: finalize_agent_response(state)
        E-->>G: summary-only response
    else search_web/refine_and_search/navigate_deeper
        G->>S: run_search_node(state)
        S->>SS: search(query, max_results)
        SS->>T: POST /search
        T-->>SS: normalized result payload
        SS-->>S: SearchResponse
        S-->>G: search_results
        G->>S: select_sources_node(state)
        S-->>G: selected_sources
        G->>F: fetch_sources_node(state)
        F-->>G: fetched_sources
        G->>E: extract_sources_node(state)
        E-->>G: extracted_sources
        G->>E: finalize_agent_response(state)
        E-->>G: AgentResponse payload
    end

    G-->>R: AgentResponse
    R-->>U: JSON response
```

### Current LangGraph Shape

```mermaid
flowchart LR
    Start((START)) --> PlannerNode[planner]
    PlannerNode -->|answer_from_context| Finalize[finalize]
    PlannerNode -->|search_web / refine_and_search / navigate_deeper| SearchNode[search]
    SearchNode --> SelectSources[select_sources]
    SelectSources --> FetchSources[fetch_sources]
    FetchSources --> ExtractSources[extract_sources]
    ExtractSources --> Finalize
    Finalize --> End((END))
```

## Design Principles

### Local-first development

The system should be easy to run on a local machine with minimal setup and environment-based configuration.

### Webpage-style output

The result should feel like a generated webpage, not a chat transcript.

### Structured rendering

LLM output should be transformed into structured data and rendered through controlled templates instead of returning arbitrary raw HTML directly.

### Explicit workflow boundaries

Search, extraction, synthesis, rendering, and navigation should be isolated so they can evolve independently.

### Inspectable orchestration

As the system becomes more agentic, state transitions should remain visible and debuggable rather than hidden inside opaque control flow.

## Component Responsibilities

### Web application layer

- hosts the HTTP API
- accepts prompts and future navigation events
- returns debug JSON or rendered pages
- provides health and lifecycle endpoints

FastAPI is the right fit here because it gives a simple, typed server layer and provides the browser-facing shell around the agent workflow.

### Configuration layer

- loads typed settings from environment variables
- centralizes host, port, debug mode, and provider configuration
- keeps secrets out of source control

### Search service

- integrates with the current search provider
- shapes provider requests and normalizes returned results
- maps provider-specific failures into application-visible errors

The current provider target is **Tavily**.

### Planner

- decides whether the system can answer from current context or needs retrieval
- may rewrite queries or route into a deeper navigation path
- returns structured decisions rather than final text

### Retrieval layer

- queries the search provider
- selects promising sources
- fetches selected pages
- extracts text, metadata, images, and style cues

### Synthesis layer

- converts evidence into structured page data
- produces titles, summaries, sections, cards, citations, and navigation intents
- keeps generation bounded by a known schema

This layer is still planned.

### Rendering layer

- converts structured page data into HTML
- keeps layout, styling, and safety under application control
- preserves a webpage-like presentation rather than chat output

This layer is still planned.

### Context and navigation layer

- tracks enough state for follow-up prompts and link-based navigation
- allows future turns to reuse evidence or gather additional evidence
- makes the browsing journey coherent across generated pages

This layer is still planned.

## Recommended Internal Orchestration

The workflow is a strong fit for **LangGraph** because:

- the workflow is stateful
- routing decisions are first-class
- the system naturally maps to bounded nodes like planner, search, fetch, extract, synthesize, and render
- graph state is easier to debug than hidden agent loops

The project should prefer a constrained graph over an open-ended autonomous loop.

## Current File-to-Responsibility Map

- `src\agentic_browser\main.py`: creates the FastAPI app and includes routes
- `src\agentic_browser\routes\agent.py`: accepts `POST /agent` requests and invokes the workflow
- `src\agentic_browser\routes\search.py`: debug/internal route for direct search calls
- `src\agentic_browser\agent\graph.py`: builds and runs the LangGraph workflow
- `src\agentic_browser\agent\planner.py`: makes the current heuristic planner decision
- `src\agentic_browser\agent\nodes\search.py`: executes search and source selection
- `src\agentic_browser\agent\nodes\fetch.py`: fetches the selected source pages
- `src\agentic_browser\agent\nodes\extract.py`: extracts evidence and assembles the final response payload
- `src\agentic_browser\services\search.py`: provider integration and search result normalization

## Package Direction

```text
agentic-browser/
├── docs/
├── src/
│   └── agentic_browser/
│       ├── agent/
│       ├── models/
│       ├── rendering/
│       ├── routes/
│       └── services/
├── tests/
├── .env.example
├── pyproject.toml
├── requirements.txt
└── run.py
```

## Error Handling Strategy

- fail fast on invalid configuration
- surface provider failures explicitly
- avoid broad catch-and-ignore patterns
- preserve enough detail for local debugging

## Security and Safety Notes

- secrets must come from environment variables
- structured rendering is preferred over raw LLM HTML
- extracted external content should be sanitized before rendering

## Open Design Questions

- what validated page schema should the synthesis step produce
- how source selection should evolve before synthesis
- how much style extraction should influence rendering in early versions
- what session storage model should back navigation context

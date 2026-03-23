# Agentic Browser Implementation Plan

## Purpose

This document tracks **project progress**, **implementation phases**, and the recommended build order.

It focuses on **what has been implemented**, **what comes next**, and **how the project should be delivered over time**.

For architecture and design rationale, see `docs\design.md`.

## Current Checkpoint

The current branch now includes:

- FastAPI application bootstrap
- environment-backed configuration
- `GET /`, `GET /health`, `GET /search`, and `POST /agent`
- Tavily-backed search integration
- normalized search, agent, and page models
- an initial LangGraph workflow with planner, search, fetch, extraction, synthesis, and finalize nodes
- runtime request and workflow logging
- tests for health, search, planner behavior, graph execution, and page-model validation

What is still missing from the long-term target:

- final HTML rendering from the synthesized page schema
- context-aware navigation across generated pages

## Phase Overview

```mermaid
flowchart LR
    Phase1[Phase 1<br/>Foundation]
    Phase2[Phase 2<br/>Search slice]
    Phase3[Phase 3<br/>Agent workflow]
    Phase4[Phase 4<br/>Structured synthesis]
    Phase5[Phase 5<br/>Rendering]
    Phase6[Phase 6<br/>Navigation]
    Phase7[Phase 7<br/>Refinement]
    Phase8[Phase 8<br/>Evaluation]

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5 --> Phase6 --> Phase7 --> Phase8
```

## Phase Roadmap

### Phase 1: Foundation

Scope:

- project scaffold
- FastAPI app bootstrap
- environment configuration
- root and health routes
- initial tests

Status: complete

### Phase 2: Search Slice

Scope:

- normalized search models
- search service abstraction
- Tavily-backed search route
- tests for route and normalization behavior

Status: complete as an initial slice

### Phase 3: Agent Workflow

Scope:

- planner state and decision model
- search, fetch, and extraction nodes
- bounded LangGraph orchestration
- `POST /agent`
- tests for workflow transitions and route behavior

Status: initial slice implemented

### Phase 4: Structured Synthesis

Scope:

- evidence packet assembly
- structured page schema
- synthesis step producing page data instead of free text

Status: initial slice implemented

### Phase 5: Rendering

Scope:

- render structured page data into HTML
- webpage-style layout for summaries, sections, citations, related links, and media

Status: next

### Phase 6: Context-Aware Navigation

Scope:

- preserve page and evidence context
- feed follow-up prompts and clicks back into the workflow

Status: planned

### Phase 7: Refinement

Scope:

- better source selection
- better image and style extraction
- latency, caching, and quality improvements

Status: planned

### Phase 8: Evaluation and Optimization

Scope:

- quality evaluation
- latency tuning
- caching
- cost controls
- robustness improvements

Status: planned

## Current Workflow Shape

```mermaid
flowchart LR
    Start((START)) --> PlannerNode[planner]
    PlannerNode -->|answer_from_context| SynthesizeNode[synthesize]
    PlannerNode -->|search_web/refine_and_search/navigate_deeper| SearchNode[search]
    SearchNode --> SelectSources[select_sources]
    SelectSources --> FetchSources[fetch_sources]
    FetchSources --> ExtractSources[extract_sources]
    ExtractSources --> SynthesizeNode
    SynthesizeNode --> Finalize
    Finalize --> End((END))
```

## Recommended Build Order

1. Add HTML rendering from structured page data.
2. Add a first end-to-end rendered page path.
3. Add navigation and context continuity.
4. Improve image and style handling in the rendered output.
5. Improve relevance, latency, and robustness.

## Near-Term Next Step

The next practical milestone is **Phase 5: Rendering**.

That phase should produce:

- a renderer that accepts `SynthesizedPage`
- deterministic HTML output for title, summary, sections, citations, links, and media
- tests around rendering output shape and key content blocks
- a clean handoff into later navigation work

## Definition of Done by Milestone

### Search slice done

- search requests return normalized results
- provider failures map to explicit errors
- route behavior is covered by tests

### Agent workflow done

- planner returns a structured decision
- the workflow can trigger retrieval when needed
- state moves predictably across workflow steps

### Structured synthesis done

- evidence is converted into validated page data
- the response format is stable enough for rendering

### Rendering done

- structured page data is converted into a webpage-like HTML response
- citations and navigation links are preserved in the rendered output

### Navigation done

- follow-up interactions reuse context when appropriate
- users can drill deeper without restarting from scratch

## Notes

- keep the implementation local-first and simple to run
- prefer additive refactors over rewrites
- keep the public README lightweight and move detailed progress tracking here

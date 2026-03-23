from __future__ import annotations

from typing import TypedDict

from agentic_browser.models.agent import (
    AgentRequest,
    AgentResponse,
    ExtractedSource,
    FetchedSource,
    PlannerOutput,
)
from agentic_browser.models.page import SynthesizedPage
from agentic_browser.models.search import SearchResult


class AgentGraphState(TypedDict, total=False):
    request: AgentRequest
    planner: PlannerOutput
    search_results: list[SearchResult]
    selected_sources: list[SearchResult]
    fetched_sources: list[FetchedSource]
    extracted_sources: list[ExtractedSource]
    page: SynthesizedPage
    response: AgentResponse

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from agentic_browser.models.search import SearchResult


class AgentDecision(str, Enum):
    ANSWER_FROM_CONTEXT = "answer_from_context"
    SEARCH_WEB = "search_web"
    REFINE_AND_SEARCH = "refine_and_search"
    NAVIGATE_DEEPER = "navigate_deeper"


class AgentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The prompt to handle.")
    context_summary: Optional[str] = Field(
        default=None,
        description="Optional summary of the current page or session context.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of search results to retrieve.",
    )
    max_sources: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of sources to fetch and extract.",
    )


class PlannerOutput(BaseModel):
    decision: AgentDecision
    reasoning: str
    search_queries: list[str] = Field(default_factory=list)
    source_limit: int = Field(default=3, ge=1, le=5)


class FetchedSource(BaseModel):
    title: str
    url: str
    snippet: str = ""
    html: Optional[str] = None
    status: str = "fetched"
    error: Optional[str] = None


class ExtractedSource(BaseModel):
    title: str
    url: str
    snippet: str = ""
    content_preview: str = ""
    headings: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    style_hints: dict[str, str] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    prompt: str
    planner: PlannerOutput
    search_results: list[SearchResult] = Field(default_factory=list)
    selected_sources: list[SearchResult] = Field(default_factory=list)
    extracted_sources: list[ExtractedSource] = Field(default_factory=list)
    summary: str

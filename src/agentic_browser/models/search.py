from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, description="The search query.")
    limit: int = Field(default=5, ge=1, le=10, description="Maximum number of results.")


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str = "tavily"


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[SearchResult]

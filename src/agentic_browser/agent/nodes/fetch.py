from __future__ import annotations

from dataclasses import dataclass

import httpx

from agentic_browser.agent.state import AgentGraphState
from agentic_browser.models.agent import FetchedSource
from agentic_browser.models.search import SearchResult


@dataclass
class PageFetcher:
    timeout: float = 10.0

    async def fetch_sources(self, sources: list[SearchResult]) -> list[FetchedSource]:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            fetched_sources: list[FetchedSource] = []

            for source in sources:
                try:
                    response = await client.get(source.url)
                    response.raise_for_status()
                    fetched_sources.append(
                        FetchedSource(
                            title=source.title,
                            url=source.url,
                            snippet=source.snippet,
                            html=response.text,
                        )
                    )
                except httpx.HTTPError as exc:
                    fetched_sources.append(
                        FetchedSource(
                            title=source.title,
                            url=source.url,
                            snippet=source.snippet,
                            status="failed",
                            error=str(exc),
                        )
                    )

        return fetched_sources


async def fetch_sources_node(
    state: AgentGraphState,
    fetcher: PageFetcher,
) -> AgentGraphState:
    selected_sources = state.get("selected_sources", [])
    fetched_sources = await fetcher.fetch_sources(selected_sources)
    return {"fetched_sources": fetched_sources}

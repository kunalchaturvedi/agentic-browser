from __future__ import annotations

from dataclasses import dataclass
import logging

import httpx

from agentic_browser.config import Settings, get_settings
from agentic_browser.models.search import SearchResponse, SearchResult

logger = logging.getLogger("uvicorn.error")


class SearchConfigurationError(Exception):
    """Raised when required search configuration is missing."""


@dataclass
class SearchService:
    settings: Settings

    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        logger.info("SearchService.search started query=%r limit=%s", query, limit)
        if not self.settings.tavily_api_key:
            raise SearchConfigurationError("Tavily API key is not configured.")

        payload = await self._fetch_results(query=query, limit=limit)
        response = self._normalize_results(query=query, payload=payload)
        logger.info(
            "SearchService.search finished query=%r normalized_results=%s",
            query,
            response.total_results,
        )
        return response

    async def _fetch_results(self, query: str, limit: int) -> dict:
        headers = {
            "Authorization": f"Bearer {self.settings.tavily_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "max_results": limit,
            "search_depth": "basic",
        }
        logger.info(
            "Calling Tavily search endpoint endpoint=%s query=%r max_results=%s",
            self.settings.tavily_search_endpoint,
            query,
            limit,
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.settings.tavily_search_endpoint,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            logger.info(
                "Tavily search call succeeded query=%r status_code=%s",
                query,
                response.status_code,
            )
            return response.json()

    def _normalize_results(self, query: str, payload: dict) -> SearchResponse:
        values = payload.get("results", [])
        results = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "") or item.get("snippet", ""),
            )
            for item in values
            if item.get("title") and item.get("url")
        ]

        return SearchResponse(
            query=query,
            total_results=len(results),
            results=results,
        )


def get_search_service() -> SearchService:
    return SearchService(settings=get_settings())

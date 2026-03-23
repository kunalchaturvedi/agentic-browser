import httpx
from fastapi.testclient import TestClient

from agentic_browser.main import app
from agentic_browser.models.search import SearchResponse, SearchResult
from agentic_browser.routes.search import get_search_service
from agentic_browser.services.search import SearchConfigurationError, SearchService


client = TestClient(app)


class StubSearchService:
    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        return SearchResponse(
            query=query,
            total_results=1,
            results=[
                SearchResult(
                    title="Example Result",
                    url="https://example.com",
                    snippet=f"Query was {query} with limit {limit}",
                )
            ],
        )


class MissingConfigSearchService:
    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        raise SearchConfigurationError("Tavily API key is not configured.")


class ProviderFailureSearchService:
    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(status_code=500, request=request)
        raise httpx.HTTPStatusError("provider error", request=request, response=response)


def test_search_route_returns_normalized_results() -> None:
    app.dependency_overrides[get_search_service] = lambda: StubSearchService()

    response = client.get("/search?q=agentic%20browser&limit=3")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "query": "agentic browser",
        "total_results": 1,
        "results": [
            {
                "title": "Example Result",
                "url": "https://example.com",
                "snippet": "Query was agentic browser with limit 3",
                "source": "tavily",
            }
        ],
    }


def test_search_route_surfaces_missing_configuration() -> None:
    app.dependency_overrides[get_search_service] = lambda: MissingConfigSearchService()

    response = client.get("/search?q=agentic%20browser")

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Tavily API key is not configured."
    }


def test_search_route_maps_provider_errors() -> None:
    app.dependency_overrides[get_search_service] = lambda: ProviderFailureSearchService()

    response = client.get("/search?q=agentic%20browser")

    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Search provider returned an error."}


def test_search_service_normalizes_tavily_payload() -> None:
    service = SearchService(
        settings=type(
            "SettingsStub",
            (),
            {
                "tavily_api_key": "test-key",
                "tavily_search_endpoint": "https://example.com/search",
            },
        )(),
    )

    payload = {
        "results": [
            {
                "title": "First Result",
                "url": "https://example.com/one",
                "content": "First snippet",
            },
            {
                "title": "Second Result",
                "url": "https://example.com/two",
                "content": "Second snippet",
            },
        ]
    }

    response = service._normalize_results(query="agentic browser", payload=payload)

    assert response == SearchResponse(
        query="agentic browser",
        total_results=2,
        results=[
            SearchResult(
                title="First Result",
                url="https://example.com/one",
                snippet="First snippet",
            ),
            SearchResult(
                title="Second Result",
                url="https://example.com/two",
                snippet="Second snippet",
            ),
        ],
    )

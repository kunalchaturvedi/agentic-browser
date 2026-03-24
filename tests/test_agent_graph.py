import asyncio

from fastapi.testclient import TestClient

from agentic_browser.agent.graph import AgentWorkflow
from agentic_browser.main import app
from agentic_browser.models.agent import AgentRequest, AgentResponse, FetchedSource
from agentic_browser.models.page import RelatedLink, SynthesizedPage
from agentic_browser.navigation import InMemoryNavigationStore, get_navigation_store
from agentic_browser.rendering import get_renderer
from agentic_browser.models.search import SearchResponse, SearchResult
from agentic_browser.routes.agent import get_agent_workflow


class StubSearchService:
    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        return SearchResponse(
            query=query,
            total_results=2,
            results=[
                SearchResult(
                    title="Example One",
                    url="https://example.com/one",
                    snippet="Snippet one",
                ),
                SearchResult(
                    title="Example Two",
                    url="https://example.com/two",
                    snippet="Snippet two",
                ),
            ],
        )


class GuardSearchService:
    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        raise AssertionError("Search should not be called for context-only prompts")


class StubFetcher:
    async def fetch_sources(self, sources: list[SearchResult]) -> list[FetchedSource]:
        return [
            FetchedSource(
                title=source.title,
                url=source.url,
                snippet=source.snippet,
                html=f"""
                <html>
                  <head>
                    <title>{source.title}</title>
                    <meta name="theme-color" content="#112233" />
                    <meta property="og:image" content="/hero.png" />
                  </head>
                  <body class="article-page">
                    <h1>{source.title}</h1>
                    <h2>Overview</h2>
                    <p>{source.snippet}</p>
                    <p>Extra context for {source.title}</p>
                    <img src="/inline.png" />
                  </body>
                </html>
                """,
            )
            for source in sources
        ]


client = TestClient(app)


def test_agent_workflow_runs_retrieval_path() -> None:
    workflow = AgentWorkflow(
        search_service=StubSearchService(),
        fetcher=StubFetcher(),
    )

    response = asyncio.run(
        workflow.run(AgentRequest(prompt="latest agentic browser news"))
    )

    assert response.planner.decision.value in {"search_web", "refine_and_search"}
    assert len(response.search_results) == 2
    assert len(response.selected_sources) >= 1
    assert len(response.extracted_sources) >= 1
    assert response.extracted_sources[0].style_hints["theme_color"] == "#112233"
    assert response.extracted_sources[0].image_urls[0] == "https://example.com/hero.png"
    assert response.page.title == "Example One"
    assert len(response.page.sections) >= 1
    assert response.page.citations[0] == "https://example.com/one"


def test_agent_workflow_skips_retrieval_for_context_prompt() -> None:
    workflow = AgentWorkflow(
        search_service=GuardSearchService(),
        fetcher=StubFetcher(),
    )

    response = asyncio.run(
        workflow.run(
            AgentRequest(
                prompt="summarize this page",
                context_summary="This page is already loaded.",
            )
        )
    )

    assert response.planner.decision.value == "answer_from_context"
    assert response.search_results == []
    assert response.page.hero_summary == "This page is already loaded."
    assert response.page.sections[0].title == "Current context"
    assert "without web retrieval" in response.summary


class StubWorkflow:
    def __init__(self) -> None:
        self.requests: list[AgentRequest] = []

    async def run(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(
            prompt=request.prompt,
            planner={
                "decision": "search_web",
                "reasoning": "Search is needed.",
                "search_queries": [request.prompt],
                "source_limit": 2,
            },
            search_results=[],
            selected_sources=[],
            extracted_sources=[],
            page=SynthesizedPage(
                title="Stub page",
                hero_summary="Stub summary",
                sections=[],
                citations=[],
                related_links=[
                    RelatedLink(
                        label="Deep dive source",
                        url="https://example.com/deep-dive",
                        snippet="Explore more details",
                        follow_up_prompt="Tell me more about Deep dive source",
                    )
                ],
            ),
            summary="Stub response",
        )


def test_agent_route_returns_structured_response() -> None:
    workflow = StubWorkflow()
    store = InMemoryNavigationStore()
    app.dependency_overrides[get_agent_workflow] = lambda: workflow
    app.dependency_overrides[get_navigation_store] = lambda: store

    response = client.post(
        "/agent",
        json={"prompt": "find agentic browser examples", "max_results": 3},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["planner"]["decision"] == "search_web"
    assert response.json()["page"]["title"] == "Stub page"
    assert response.json()["summary"] == "Stub response"
    assert response.json()["session_id"]
    assert response.json()["page_id"]
    assert response.json()["page"]["session_id"] == response.json()["session_id"]
    assert response.json()["page"]["page_id"] == response.json()["page_id"]
    assert store.get_page(response.json()["session_id"], response.json()["page_id"]) is not None


class StubRenderer:
    def render(self, page: SynthesizedPage) -> str:
        return f"<html><body><h1>{page.title}</h1></body></html>"


def test_agent_render_route_returns_html() -> None:
    store = InMemoryNavigationStore()
    app.dependency_overrides[get_agent_workflow] = lambda: StubWorkflow()
    app.dependency_overrides[get_renderer] = lambda: StubRenderer()
    app.dependency_overrides[get_navigation_store] = lambda: store

    response = client.post(
        "/agent/render",
        json={"prompt": "find agentic browser examples", "max_results": 3},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<h1>Stub page</h1>" in response.text


def test_agent_render_route_emits_navigation_links_and_permalink() -> None:
    store = InMemoryNavigationStore()
    app.dependency_overrides[get_agent_workflow] = lambda: StubWorkflow()
    app.dependency_overrides[get_navigation_store] = lambda: store

    response = client.post(
        "/agent/render",
        json={"prompt": "find agentic browser examples", "max_results": 3},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "/agent/follow-up?" in response.text
    assert "/agent/pages/" in response.text


def test_follow_up_route_reuses_stored_context() -> None:
    workflow = StubWorkflow()
    store = InMemoryNavigationStore()
    app.dependency_overrides[get_agent_workflow] = lambda: workflow
    app.dependency_overrides[get_navigation_store] = lambda: store

    initial_response = client.post(
        "/agent",
        json={"prompt": "find agentic browser examples", "max_results": 3},
    )
    initial_payload = initial_response.json()

    response = client.get(
        "/agent/follow-up",
        params={
            "session_id": initial_payload["session_id"],
            "current_page_id": initial_payload["page_id"],
            "target_url": "https://example.com/deep-dive",
            "target_label": "Deep dive source",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert workflow.requests[-1].context_summary == "Stub summary"
    assert workflow.requests[-1].session_id == initial_payload["session_id"]
    assert workflow.requests[-1].current_page_id == initial_payload["page_id"]
    assert "Stub page" in response.text


def test_stored_page_route_renders_saved_page() -> None:
    store = InMemoryNavigationStore()
    app.dependency_overrides[get_agent_workflow] = lambda: StubWorkflow()
    app.dependency_overrides[get_navigation_store] = lambda: store

    initial_response = client.post(
        "/agent",
        json={"prompt": "find agentic browser examples", "max_results": 3},
    )
    initial_payload = initial_response.json()

    response = client.get(
        f"/agent/pages/{initial_payload['session_id']}/{initial_payload['page_id']}"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Stub page" in response.text

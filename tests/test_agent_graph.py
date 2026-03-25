import asyncio

from fastapi.testclient import TestClient

from agentic_browser.agent.graph import AgentWorkflow
from agentic_browser.agent.nodes.synthesize import DeterministicPageSynthesizer
from agentic_browser.agent.planner import HeuristicAgentPlanner
from agentic_browser.main import app
from agentic_browser.models.agent import AgentDecision
from agentic_browser.models.agent import AgentRequest, AgentResponse, FetchedSource
from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage
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


class RecipeStubFetcher:
    async def fetch_sources(self, sources: list[SearchResult]) -> list[FetchedSource]:
        return [
            FetchedSource(
                title="Banana Shake Recipe",
                url="https://example.com/banana-shake",
                snippet="A simple banana shake recipe.",
                html="""
                <html>
                  <head>
                    <title>Banana Shake Recipe</title>
                    <meta property="og:image" content="/banana-shake.jpg" />
                    <script type="application/ld+json">
                    {
                      "@context": "https://schema.org",
                      "@type": "Recipe",
                      "description": "A creamy banana shake recipe.",
                      "recipeIngredient": ["2 bananas", "1 cup milk", "1 tsp honey"],
                      "recipeInstructions": [
                        "Add bananas to the blender.",
                        "Pour in milk and honey.",
                        "Blend until smooth."
                      ]
                    }
                    </script>
                  </head>
                  <body>
                    <h1>Banana Shake Recipe</h1>
                    <p>Blend ripe bananas with milk for a creamy drink.</p>
                  </body>
                </html>
                """,
            )
        ]


class HowToStubFetcher:
    async def fetch_sources(self, sources: list[SearchResult]) -> list[FetchedSource]:
        return [
            FetchedSource(
                title="Set Up Python Virtual Environment",
                url="https://example.com/python-venv",
                snippet="Create an isolated Python environment for your project.",
                html="""
                <html>
                  <body>
                    <h1>Set Up Python Virtual Environment</h1>
                    <h2>Prerequisites</h2>
                    <h2>Create the Environment</h2>
                    <ul>
                      <li>Install Python on your machine.</li>
                      <li>Open a terminal in the project folder.</li>
                      <li>Activate the environment before installing packages.</li>
                    </ul>
                    <p>Install Python, open a terminal, and navigate to your project folder.</p>
                    <p>Run python -m venv .venv and then activate the environment before installing dependencies.</p>
                    <p>Verify the environment is active before continuing.</p>
                  </body>
                </html>
                """,
            )
        ]


class ComparisonStubFetcher:
    async def fetch_sources(self, sources: list[SearchResult]) -> list[FetchedSource]:
        return [
            FetchedSource(
                title="VS Code vs PyCharm",
                url="https://example.com/vscode-vs-pycharm",
                snippet="Compare lightweight editing with an integrated Python IDE experience.",
                html="""
                <html>
                  <body>
                    <h1>VS Code vs PyCharm</h1>
                    <h2>Editor Footprint</h2>
                    <h2>Python Tooling</h2>
                    <ul>
                      <li>VS Code starts lighter and stays highly extensible.</li>
                      <li>PyCharm includes more built-in Python workflows.</li>
                    </ul>
                    <p>VS Code is lighter and more extensible, while PyCharm ships with more batteries included for Python workflows.</p>
                    <p>PyCharm often provides stronger built-in refactoring, but VS Code can be more flexible across languages.</p>
                  </body>
                </html>
                """,
            ),
            FetchedSource(
                title="Choosing a Python IDE",
                url="https://example.com/python-ide-choice",
                snippet="Pick the tool that best matches your workflow and team needs.",
                html="""
                <html>
                  <body>
                    <h1>Choosing a Python IDE</h1>
                    <p>Teams that want one editor for many stacks may prefer VS Code, while Python-heavy teams may prefer PyCharm.</p>
                  </body>
                </html>
                """,
            ),
        ]


class ReviewStubFetcher:
    async def fetch_sources(self, sources: list[SearchResult]) -> list[FetchedSource]:
        return [
            FetchedSource(
                title="MacBook Air M5 Review",
                url="https://example.com/macbook-air-review",
                snippet="A thin laptop with strong battery life and a higher price than entry-level alternatives.",
                html="""
                <html>
                  <body>
                    <h1>MacBook Air M5 Review</h1>
                    <h2>Design</h2>
                    <h2>Performance</h2>
                    <h2>Value</h2>
                    <ul>
                      <li>Thin and travel-friendly design.</li>
                      <li>Fast everyday performance with long battery life.</li>
                      <li>Higher asking price, but strong overall polish.</li>
                      <li>Best suited for students, office work, and portable productivity.</li>
                    </ul>
                    <p>The laptop feels premium and easy to carry.</p>
                    <p>Its performance is strong for mainstream work, though not ideal for the heaviest graphics workloads.</p>
                    <p>It is expensive, but the overall package is well-rounded.</p>
                  </body>
                </html>
                """,
            )
        ]


client = TestClient(app)


def test_agent_workflow_runs_retrieval_path() -> None:
    workflow = AgentWorkflow(
        search_service=StubSearchService(),
        planner=HeuristicAgentPlanner(),
        fetcher=StubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
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
        planner=HeuristicAgentPlanner(),
        fetcher=StubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
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


class StubAsyncPlanner:
    async def plan(self, request: AgentRequest):  # type: ignore[no-untyped-def]
        return {
            "decision": AgentDecision.ANSWER_FROM_CONTEXT,
            "reasoning": "Current context is enough.",
            "search_queries": [],
            "source_limit": 1,
        }


def test_agent_workflow_supports_async_planner() -> None:
    workflow = AgentWorkflow(
        search_service=GuardSearchService(),
        planner=StubAsyncPlanner(),
        fetcher=StubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
    )

    response = asyncio.run(
        workflow.run(
            AgentRequest(
                prompt="use current context",
                context_summary="Current page is already loaded.",
            )
        )
    )

    assert response.planner.decision.value == "answer_from_context"
    assert response.search_results == []


class StubAsyncSynthesizer:
    async def synthesize(self, state):  # type: ignore[no-untyped-def]
        return {
            "title": "Synthesized by LLM",
            "hero_summary": "Structured page from async synthesizer.",
            "sections": [
                {
                    "title": "LLM section",
                    "body": "Generated content.",
                    "bullets": [],
                    "citations": [],
                }
            ],
            "citations": [],
            "related_links": [],
            "hero_image_url": None,
            "theme_hints": {},
            "context_summary": "Structured page from async synthesizer.",
        }


def test_agent_workflow_supports_async_synthesizer() -> None:
    workflow = AgentWorkflow(
        search_service=GuardSearchService(),
        planner=StubAsyncPlanner(),
        synthesizer=StubAsyncSynthesizer(),
        fetcher=StubFetcher(),
    )

    response = asyncio.run(
        workflow.run(
            AgentRequest(
                prompt="use current context",
                context_summary="Current page is already loaded.",
            )
        )
    )

    assert response.page.title == "Synthesized by LLM"
    assert response.page.sections[0].title == "LLM section"


def test_agent_workflow_builds_coherent_recipe_sections() -> None:
    workflow = AgentWorkflow(
        search_service=StubSearchService(),
        planner=HeuristicAgentPlanner(),
        fetcher=RecipeStubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
    )

    response = asyncio.run(workflow.run(AgentRequest(prompt="Give me a recipe for banana shake")))

    section_titles = [section.title for section in response.page.sections]
    assert response.planner.page_intent.value == "recipe"
    assert "Ingredients" in section_titles
    assert "Method" in section_titles
    ingredients_section = next(section for section in response.page.sections if section.title == "Ingredients")
    method_section = next(section for section in response.page.sections if section.title == "Method")
    assert "2 bananas" in ingredients_section.bullets
    assert "Blend until smooth." in method_section.bullets


def test_agent_workflow_builds_how_to_sections() -> None:
    workflow = AgentWorkflow(
        search_service=StubSearchService(),
        planner=HeuristicAgentPlanner(),
        fetcher=HowToStubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
    )

    response = asyncio.run(workflow.run(AgentRequest(prompt="How to set up a python virtual environment")))

    section_titles = [section.title for section in response.page.sections]
    assert response.planner.page_intent.value == "how_to"
    assert "What You'll Need" in section_titles
    assert "Steps" in section_titles
    assert "Verify Installation" in section_titles
    steps_section = next(section for section in response.page.sections if section.title == "Steps")
    assert "Install Python on your machine." in steps_section.bullets


def test_agent_workflow_builds_comparison_sections() -> None:
    workflow = AgentWorkflow(
        search_service=StubSearchService(),
        planner=HeuristicAgentPlanner(),
        fetcher=ComparisonStubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
    )

    response = asyncio.run(workflow.run(AgentRequest(prompt="Compare VS Code versus PyCharm for Python")))

    section_titles = [section.title for section in response.page.sections]
    assert response.planner.page_intent.value == "comparison"
    assert "Options Compared" in section_titles
    assert "Key Differences" in section_titles
    differences_section = next(section for section in response.page.sections if section.title == "Key Differences")
    assert "VS Code starts lighter and stays highly extensible." in differences_section.bullets


def test_agent_workflow_builds_review_sections() -> None:
    workflow = AgentWorkflow(
        search_service=StubSearchService(),
        planner=HeuristicAgentPlanner(),
        fetcher=ReviewStubFetcher(),
        synthesizer=DeterministicPageSynthesizer(),
    )

    response = asyncio.run(
        workflow.run(
            AgentRequest(
                prompt="Review the latest MacBook Air and include design, performance, price, and who it is for"
            )
        )
    )

    section_titles = [section.title for section in response.page.sections]
    assert response.planner.page_intent.value == "review"
    assert "Design and Everyday Use" in section_titles
    assert "Performance" in section_titles
    assert "Price and Value" in section_titles
    assert "Who This Is For" in section_titles


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
    assert "http://127.0.0.1:8000/agent/follow-up?" in response.text
    assert "http://127.0.0.1:8000/agent/pages/" in response.text


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

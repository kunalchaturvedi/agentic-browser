import asyncio
import json

import httpx
import pytest

from agentic_browser.agent.nodes.synthesize import (
    DeterministicPageSynthesizer,
    LlmPageSynthesizer,
)
from agentic_browser.config import Settings
from agentic_browser.models.agent import AgentDecision, AgentRequest, ExtractedSource, PlannerOutput
from agentic_browser.models.search import SearchResult
from agentic_browser.services.llm import AzureAISynthesisService, SynthesisServiceError


def build_settings() -> Settings:
    return Settings(
        azure_openai_endpoint="https://example-resource.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_deployment_name="gpt-4.1-mini",
        azure_openai_api_version="2025-01-01-preview",
    )


def build_request() -> AgentRequest:
    return AgentRequest(prompt="Summarize the latest agentic browser trends", max_sources=3)


def build_planner_output() -> PlannerOutput:
    return PlannerOutput(
        decision=AgentDecision.SEARCH_WEB,
        reasoning="Fresh evidence is needed.",
        search_queries=["latest agentic browser trends"],
        source_limit=3,
    )


def build_selected_sources() -> list[SearchResult]:
    return [
        SearchResult(title="Example One", url="https://example.com/one", snippet="Snippet one"),
        SearchResult(title="Example Two", url="https://example.com/two", snippet="Snippet two"),
    ]


def build_extracted_sources() -> list[ExtractedSource]:
    return [
        ExtractedSource(
            title="Example One",
            url="https://example.com/one",
            snippet="Snippet one",
            content_preview="Agentic browsers are shifting toward tool use and richer navigation.",
            headings=["Overview", "Capabilities", "Outlook"],
            citations=["https://example.com/one"],
            image_urls=["https://example.com/hero.png"],
            style_hints={"theme_color": "#112233"},
        )
    ]


def test_azure_synthesis_service_parses_and_sanitizes_valid_response(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AzureAISynthesisService(settings=build_settings())

    async def fake_post(self, url, *, params=None, headers=None, json=None):  # type: ignore[no-untyped-def]
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "title": "Agentic Browser Trends",
                                    "hero_summary": "Agentic browsers are becoming more workflow-oriented.",
                                    "sections": [
                                        {
                                            "title": "Overview",
                                            "body": "They combine planning, retrieval, and action.",
                                            "bullets": ["Planning", "Retrieval"],
                                            "citations": ["https://example.com/one", "https://invented.example"],
                                        }
                                    ],
                                    "citations": ["https://example.com/one", "https://invented.example"],
                                    "related_links": [
                                        {
                                            "label": "Example One",
                                            "url": "https://example.com/one",
                                            "snippet": "Snippet one",
                                            "follow_up_prompt": "Tell me more about Example One",
                                        },
                                        "https://example.com/two",
                                        "https://invented.example",
                                    ],
                                    "hero_image_url": "https://example.com/hero.png",
                                    "theme_hints": [],
                                    "context_summary": "A concise trend summary.",
                                }
                            )
                        }
                    }
                ]
            },
        )

    json_module = json
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    page = asyncio.run(
        service.synthesize(
            request=build_request(),
            planner=build_planner_output(),
            extracted_sources=build_extracted_sources(),
            selected_sources=build_selected_sources(),
        )
    )

    assert page.title == "Agentic Browser Trends"
    assert page.sections[0].citations == ["https://example.com/one"]
    assert page.citations == ["https://example.com/one"]
    assert page.related_links[0].url == "https://example.com/one"
    assert page.related_links[1].url == "https://example.com/two"
    assert all(link.url != "https://invented.example" for link in page.related_links)
    assert page.hero_image_url == "https://example.com/hero.png"
    assert page.theme_hints["theme_color"] == "#112233"
    assert page.synthesis_mode == "llm"


def test_azure_synthesis_service_rejects_invalid_response_payload() -> None:
    service = AzureAISynthesisService(settings=build_settings())

    with pytest.raises(SynthesisServiceError):
        service._parse_response(  # noqa: SLF001
            request=build_request(),
            planner=build_planner_output(),
            payload={"choices": [{"message": {"content": '{"title":"Bad Page"}'}}]},
            extracted_sources=build_extracted_sources(),
            selected_sources=build_selected_sources(),
        )


def test_azure_synthesis_service_drops_white_theme_color() -> None:
    service = AzureAISynthesisService(settings=build_settings())

    page = service._parse_response(  # noqa: SLF001
        request=build_request(),
        planner=build_planner_output(),
        payload={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "Agentic Browser Trends",
                                "hero_summary": "Summary",
                                "sections": [
                                    {
                                        "title": "Overview",
                                        "body": "Body",
                                        "bullets": [],
                                        "citations": ["https://example.com/one"],
                                    }
                                ],
                                "citations": ["https://example.com/one"],
                                "related_links": [],
                                "hero_image_url": "https://example.com/hero.png",
                                "theme_hints": {"theme_color": "#FFFFFF"},
                                "context_summary": "Summary",
                            }
                        )
                    }
                }
            ]
        },
        extracted_sources=build_extracted_sources(),
        selected_sources=build_selected_sources(),
    )

    assert page.theme_hints == {"theme_color": "#112233"}


def test_azure_synthesis_service_rejects_non_json_http_response(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AzureAISynthesisService(settings=build_settings())

    async def fake_post(self, url, *, params=None, headers=None, json=None):  # type: ignore[no-untyped-def]
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, content=b"not json")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(SynthesisServiceError, match="non-JSON"):
        asyncio.run(
            service.synthesize(
                request=build_request(),
                planner=build_planner_output(),
                extracted_sources=build_extracted_sources(),
                selected_sources=build_selected_sources(),
            )
        )


def test_llm_synthesizer_falls_back_to_deterministic_synthesis() -> None:
    class FailingService:
        async def synthesize(self, request, planner, extracted_sources, selected_sources):  # type: ignore[no-untyped-def]
            raise SynthesisServiceError("invalid synthesis response")

    synthesizer = LlmPageSynthesizer(
        service=FailingService(),
        fallback=DeterministicPageSynthesizer(),
    )

    page = asyncio.run(
        synthesizer.synthesize(
            {
                "request": AgentRequest(prompt="summarize this page", context_summary="Current page."),
                "planner": PlannerOutput(
                    decision=AgentDecision.ANSWER_FROM_CONTEXT,
                    reasoning="Current context is enough.",
                    search_queries=[],
                    source_limit=1,
                ),
                "selected_sources": [],
                "extracted_sources": [],
            }
        )
    )

    assert page.sections[0].title == "Current context"


def test_azure_synthesis_service_prefers_step_specific_deployment_name() -> None:
    service = AzureAISynthesisService(
        settings=Settings(
            azure_openai_endpoint="https://example-resource.openai.azure.com",
            azure_openai_api_key="test-key",
            azure_openai_deployment_name="shared-model",
            azure_openai_synthesis_deployment_name="synthesis-model",
            azure_openai_api_version="2025-01-01-preview",
        )
    )

    assert service.is_configured()
    assert service.settings.synthesis_deployment_name == "synthesis-model"

import asyncio
import json
import logging

import httpx
import pytest

from agentic_browser.agent.planner import HeuristicAgentPlanner, LlmAgentPlanner
from agentic_browser.config import Settings
from agentic_browser.models.agent import AgentRequest
from agentic_browser.services.llm import AzureAIPlannerService, PlannerServiceError


def build_settings() -> Settings:
    return Settings(
        azure_openai_endpoint="https://example-resource.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_deployment_name="gpt-4.1-mini",
        azure_openai_api_version="2024-10-21",
    )


def test_azure_planner_service_plan_parses_valid_response(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AzureAIPlannerService(settings=build_settings())

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
                                    "decision": "search_web",
                                    "reasoning": "Fresh web information is needed.",
                                    "search_queries": ["latest agentic browser news"],
                                    "source_limit": 4,
                                }
                            )
                        }
                    }
                ]
            },
        )

    json_module = json
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = asyncio.run(service.plan(AgentRequest(prompt="latest agentic browser news", max_sources=3)))

    assert response.decision.value == "search_web"
    assert response.search_queries == ["latest agentic browser news"]
    assert response.source_limit == 3


def test_azure_planner_service_rejects_invalid_response_payload() -> None:
    service = AzureAIPlannerService(settings=build_settings())

    with pytest.raises(PlannerServiceError):
        service._parse_response(  # noqa: SLF001
            AgentRequest(prompt="tell me more"),
            {"choices": [{"message": {"content": '{"decision":"search_web","reasoning":"Need search","search_queries":[],"source_limit":3}'}}]},
        )


def test_llm_planner_falls_back_to_heuristic_on_invalid_llm_output() -> None:
    class FailingService:
        async def plan(self, request: AgentRequest):  # type: ignore[no-untyped-def]
            raise PlannerServiceError("invalid planner response")

    planner = LlmAgentPlanner(service=FailingService(), fallback=HeuristicAgentPlanner())

    response = asyncio.run(planner.plan(AgentRequest(prompt="summarize this page", context_summary="Current page.")))

    assert response.decision.value == "answer_from_context"


def test_heuristic_planner_still_handles_navigation_prompt() -> None:
    planner = HeuristicAgentPlanner()

    response = planner.plan(AgentRequest(prompt="tell me more", context_summary="Current page."))

    assert response.decision.value == "navigate_deeper"


def test_azure_planner_service_logs_raw_response_in_debug(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    service = AzureAIPlannerService(settings=build_settings())

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
                                    "decision": "search_web",
                                    "reasoning": "Fresh web information is needed.",
                                    "search_queries": ["latest agentic browser news"],
                                    "source_limit": 3,
                                }
                            )
                        }
                    }
                ]
            },
        )

    json_module = json
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with caplog.at_level(logging.DEBUG, logger="uvicorn.error"):
        asyncio.run(service.plan(AgentRequest(prompt="latest agentic browser news", max_sources=3)))

    assert "Azure AI Foundry planner raw response" in caplog.text

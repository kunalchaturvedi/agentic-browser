from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Awaitable, Protocol, Union

import httpx

from agentic_browser.models.agent import AgentDecision, AgentRequest, PlannerOutput
from agentic_browser.services.llm import AzureAIPlannerService, PlannerServiceError, get_planner_service

logger = logging.getLogger("uvicorn.error")


class AgentPlanner(Protocol):
    def plan(self, request: AgentRequest) -> Union[PlannerOutput, Awaitable[PlannerOutput]]:
        ...


@dataclass
class HeuristicAgentPlanner:
    """Deterministic planner used until LLM-backed planning is introduced."""

    def plan(self, request: AgentRequest) -> PlannerOutput:
        prompt = request.prompt.strip()
        normalized = prompt.lower()
        source_limit = min(request.max_sources, 3)

        if request.context_summary and any(
            phrase in normalized
            for phrase in (
                "summarize this",
                "summarise this",
                "explain this",
                "what does this mean",
                "use current context",
            )
        ):
            output = PlannerOutput(
                decision=AgentDecision.ANSWER_FROM_CONTEXT,
                reasoning="Prompt can be handled from the current page context.",
                search_queries=[],
                source_limit=source_limit,
            )
            logger.info(
                "Planner using heuristic mode prompt=%r decision=%s has_context=%s",
                request.prompt,
                output.decision.value,
                bool(request.context_summary),
            )
            return output

        if request.context_summary and any(
            phrase in normalized
            for phrase in (
                "tell me more",
                "go deeper",
                "more about",
                "next level",
            )
        ):
            output = PlannerOutput(
                decision=AgentDecision.NAVIGATE_DEEPER,
                reasoning="Prompt appears to request deeper exploration of the current topic.",
                search_queries=[prompt],
                source_limit=source_limit,
            )
            logger.info(
                "Planner using heuristic mode prompt=%r decision=%s has_context=%s",
                request.prompt,
                output.decision.value,
                bool(request.context_summary),
            )
            return output

        if len(prompt.split()) >= 10:
            output = PlannerOutput(
                decision=AgentDecision.REFINE_AND_SEARCH,
                reasoning="Prompt is detailed enough to benefit from query refinement before retrieval.",
                search_queries=[prompt],
                source_limit=source_limit,
            )
            logger.info(
                "Planner using heuristic mode prompt=%r decision=%s has_context=%s",
                request.prompt,
                output.decision.value,
                bool(request.context_summary),
            )
            return output

        output = PlannerOutput(
            decision=AgentDecision.SEARCH_WEB,
            reasoning="Prompt needs web retrieval before the system can build a page plan.",
            search_queries=[prompt],
            source_limit=source_limit,
        )
        logger.info(
            "Planner using heuristic mode prompt=%r decision=%s has_context=%s",
            request.prompt,
            output.decision.value,
            bool(request.context_summary),
        )
        return output


@dataclass
class LlmAgentPlanner:
    service: AzureAIPlannerService
    fallback: HeuristicAgentPlanner

    async def plan(self, request: AgentRequest) -> PlannerOutput:
        deployment_name = getattr(getattr(self.service, "settings", None), "azure_openai_deployment_name", "unknown")
        try:
            logger.info(
                "Planner calling Azure AI Foundry deployment=%s prompt=%r has_context=%s",
                deployment_name,
                request.prompt,
                bool(request.context_summary),
            )
            output = await self.service.plan(request)
            logger.info(
                "Planner using Azure AI Foundry deployment=%s decision=%s",
                deployment_name,
                output.decision.value,
            )
            return output
        except PlannerServiceError as exc:
            logger.warning("Planner LLM failed, falling back to heuristic planner: %s", exc)
            return self.fallback.plan(request)
        except httpx.HTTPError as exc:
            logger.warning("Planner LLM HTTP failure, falling back to heuristic planner: %s", exc)
            return self.fallback.plan(request)


def get_agent_planner() -> AgentPlanner:
    heuristic = HeuristicAgentPlanner()
    service = get_planner_service()
    if not service.is_configured():
        logger.info("Planner initialized in heuristic mode because Azure AI Foundry is not fully configured")
        return heuristic
    logger.info(
        "Planner initialized in Azure AI Foundry mode deployment=%s",
        service.settings.azure_openai_deployment_name,
    )
    return LlmAgentPlanner(service=service, fallback=heuristic)

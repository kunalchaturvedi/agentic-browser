from __future__ import annotations

from dataclasses import dataclass

from agentic_browser.models.agent import AgentDecision, AgentRequest, PlannerOutput


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
            return PlannerOutput(
                decision=AgentDecision.ANSWER_FROM_CONTEXT,
                reasoning="Prompt can be handled from the current page context.",
                search_queries=[],
                source_limit=source_limit,
            )

        if request.context_summary and any(
            phrase in normalized
            for phrase in (
                "tell me more",
                "go deeper",
                "more about",
                "next level",
            )
        ):
            return PlannerOutput(
                decision=AgentDecision.NAVIGATE_DEEPER,
                reasoning="Prompt appears to request deeper exploration of the current topic.",
                search_queries=[prompt],
                source_limit=source_limit,
            )

        if len(prompt.split()) >= 10:
            return PlannerOutput(
                decision=AgentDecision.REFINE_AND_SEARCH,
                reasoning="Prompt is detailed enough to benefit from query refinement before retrieval.",
                search_queries=[prompt],
                source_limit=source_limit,
            )

        return PlannerOutput(
            decision=AgentDecision.SEARCH_WEB,
            reasoning="Prompt needs web retrieval before the system can build a page plan.",
            search_queries=[prompt],
            source_limit=source_limit,
        )

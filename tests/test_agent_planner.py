from agentic_browser.agent.planner import HeuristicAgentPlanner
from agentic_browser.models.agent import AgentDecision, AgentRequest


def test_planner_uses_context_when_prompt_requests_summary() -> None:
    planner = HeuristicAgentPlanner()

    result = planner.plan(
        AgentRequest(
            prompt="Summarize this page for me",
            context_summary="Current page discusses retrieval pipelines.",
        )
    )

    assert result.decision == AgentDecision.ANSWER_FROM_CONTEXT
    assert result.search_queries == []


def test_planner_refines_long_prompt_before_search() -> None:
    planner = HeuristicAgentPlanner()

    result = planner.plan(
        AgentRequest(
            prompt="Compare the latest agentic browser frameworks and explain which approach fits a hobby project best",
        )
    )

    assert result.decision == AgentDecision.REFINE_AND_SEARCH
    assert result.search_queries == [
        "Compare the latest agentic browser frameworks and explain which approach fits a hobby project best"
    ]

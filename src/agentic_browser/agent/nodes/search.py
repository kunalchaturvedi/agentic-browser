from __future__ import annotations

from agentic_browser.agent.state import AgentGraphState
from agentic_browser.services.search import SearchService


async def run_search_node(
    state: AgentGraphState,
    search_service: SearchService,
) -> AgentGraphState:
    request = state["request"]
    planner = state["planner"]
    query = planner.search_queries[0] if planner.search_queries else request.prompt
    response = await search_service.search(query=query, limit=request.max_results)

    return {"search_results": response.results}


def select_sources_node(state: AgentGraphState) -> AgentGraphState:
    planner = state["planner"]
    search_results = state.get("search_results", [])
    selected = search_results[: planner.source_limit]
    return {"selected_sources": selected}

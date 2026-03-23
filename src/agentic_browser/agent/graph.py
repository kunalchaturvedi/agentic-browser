from __future__ import annotations

from dataclasses import dataclass, field
import logging

from langgraph.graph import END, START, StateGraph

from agentic_browser.agent.nodes.extract import (
    extract_sources_node,
    finalize_agent_response,
)
from agentic_browser.agent.nodes.fetch import PageFetcher, fetch_sources_node
from agentic_browser.agent.nodes.search import run_search_node, select_sources_node
from agentic_browser.agent.nodes.synthesize import synthesize_page_node
from agentic_browser.agent.planner import HeuristicAgentPlanner
from agentic_browser.agent.state import AgentGraphState
from agentic_browser.models.agent import AgentDecision, AgentRequest, AgentResponse
from agentic_browser.services.search import SearchService, get_search_service

logger = logging.getLogger("uvicorn.error")


@dataclass
class AgentWorkflow:
    search_service: SearchService
    planner: HeuristicAgentPlanner = field(default_factory=HeuristicAgentPlanner)
    fetcher: PageFetcher = field(default_factory=PageFetcher)

    def __post_init__(self) -> None:
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentGraphState)

        graph.add_node("planner", self._planner_node)
        graph.add_node("search", self._search_node)
        graph.add_node("select_sources", select_sources_node)
        graph.add_node("fetch_sources", self._fetch_node)
        graph.add_node("extract_sources", extract_sources_node)
        graph.add_node("synthesize", synthesize_page_node)
        graph.add_node("finalize", finalize_agent_response)

        graph.add_edge(START, "planner")
        graph.add_conditional_edges(
            "planner",
            self._route_from_planner,
            {
                "search": "search",
                "synthesize": "synthesize",
            },
        )
        graph.add_edge("search", "select_sources")
        graph.add_edge("select_sources", "fetch_sources")
        graph.add_edge("fetch_sources", "extract_sources")
        graph.add_edge("extract_sources", "synthesize")
        graph.add_edge("synthesize", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    def _planner_node(self, state: AgentGraphState) -> AgentGraphState:
        request = state["request"]
        planner_output = self.planner.plan(request)
        logger.info(
            "Planner decision prompt=%r decision=%s queries=%s source_limit=%s",
            request.prompt,
            planner_output.decision.value,
            planner_output.search_queries,
            planner_output.source_limit,
        )
        return {"planner": planner_output}

    async def _search_node(self, state: AgentGraphState) -> AgentGraphState:
        return await run_search_node(state, self.search_service)

    async def _fetch_node(self, state: AgentGraphState) -> AgentGraphState:
        return await fetch_sources_node(state, self.fetcher)

    @staticmethod
    def _route_from_planner(state: AgentGraphState) -> str:
        planner = state["planner"]
        if planner.decision == AgentDecision.ANSWER_FROM_CONTEXT:
            logger.info("Planner routed workflow directly to synthesize")
            return "synthesize"
        logger.info("Planner routed workflow to search")
        return "search"

    async def run(self, request: AgentRequest) -> AgentResponse:
        logger.info("AgentWorkflow.run started prompt=%r", request.prompt)
        state = await self._graph.ainvoke({"request": request})
        response = AgentResponse.model_validate(state["response"])
        logger.info(
            "AgentWorkflow.run finished prompt=%r decision=%s",
            request.prompt,
            response.planner.decision.value,
        )
        return response


def get_agent_workflow() -> AgentWorkflow:
    return AgentWorkflow(search_service=get_search_service())

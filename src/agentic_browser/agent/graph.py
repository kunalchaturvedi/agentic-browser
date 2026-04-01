from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import logging

from langgraph.graph import END, START, StateGraph

from agentic_browser.agent.nodes.extract import (
    extract_sources_node,
    finalize_agent_response,
)
from agentic_browser.agent.nodes.fetch import PageFetcher, fetch_sources_node
from agentic_browser.agent.nodes.search import run_search_node, select_sources_node
from agentic_browser.agent.state import AgentGraphState
from agentic_browser.intelligence.interfaces import AgentPlanner, PageSynthesizer
from agentic_browser.intelligence.planner import get_agent_planner
from agentic_browser.intelligence.synthesizer import get_page_synthesizer
from agentic_browser.models.agent import AgentDecision, AgentRequest, AgentResponse, PlannerOutput
from agentic_browser.models.page import SynthesizedPage
from agentic_browser.services.search import SearchService, get_search_service

logger = logging.getLogger("uvicorn.error")


@dataclass
class AgentWorkflow:
    search_service: SearchService
    planner: AgentPlanner = field(default_factory=get_agent_planner)
    fetcher: PageFetcher = field(default_factory=PageFetcher)
    synthesizer: PageSynthesizer = field(default_factory=get_page_synthesizer)

    def __post_init__(self) -> None:
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentGraphState)

        graph.add_node("planner", self._planner_node)
        graph.add_node("search", self._search_node)
        graph.add_node("select_sources", select_sources_node)
        graph.add_node("fetch_sources", self._fetch_node)
        graph.add_node("extract_sources", extract_sources_node)
        graph.add_node("synthesize", self._synthesize_node)
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

    async def _planner_node(self, state: AgentGraphState) -> AgentGraphState:
        request = state["request"]
        planner_result = self.planner.plan(request)
        planner_output = await planner_result if inspect.isawaitable(planner_result) else planner_result
        planner_output = PlannerOutput.model_validate(planner_output)
        logger.info(
            "Planner decision prompt=%r decision=%s page_intent=%s queries=%s source_limit=%s",
            request.prompt,
            planner_output.decision.value,
            planner_output.page_intent.value,
            planner_output.search_queries,
            planner_output.source_limit,
        )
        return {"planner": planner_output}

    async def _search_node(self, state: AgentGraphState) -> AgentGraphState:
        return await run_search_node(state, self.search_service)

    async def _fetch_node(self, state: AgentGraphState) -> AgentGraphState:
        return await fetch_sources_node(state, self.fetcher)

    async def _synthesize_node(self, state: AgentGraphState) -> AgentGraphState:
        synthesis_result = self.synthesizer.synthesize(state)
        page = await synthesis_result if inspect.isawaitable(synthesis_result) else synthesis_result
        page = SynthesizedPage.model_validate(page)
        return {"page": page}

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

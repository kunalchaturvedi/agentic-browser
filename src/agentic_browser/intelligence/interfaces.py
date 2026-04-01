from __future__ import annotations

from typing import Awaitable, Protocol, Union

from agentic_browser.agent.state import AgentGraphState
from agentic_browser.models.agent import AgentRequest, PlannerOutput
from agentic_browser.models.page import RelatedLink, SynthesizedPage


class AgentPlanner(Protocol):
    def plan(self, request: AgentRequest) -> Union[PlannerOutput, Awaitable[PlannerOutput]]:
        ...


class QueryRefiner(Protocol):
    def refine(self, request: AgentRequest, planner_output: PlannerOutput) -> Union[list[str], Awaitable[list[str]]]:
        ...


class PageSynthesizer(Protocol):
    def synthesize(self, state: AgentGraphState) -> Union[SynthesizedPage, Awaitable[SynthesizedPage]]:
        ...


class FollowUpLinkGenerator(Protocol):
    def generate(self, state: AgentGraphState) -> Union[list[RelatedLink], Awaitable[list[RelatedLink]]]:
        ...

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Optional

from agentic_browser.agent.graph import AgentWorkflow, get_agent_workflow
from agentic_browser.intelligence.interfaces import AgentPlanner
from agentic_browser.intelligence.planner import get_agent_planner
from agentic_browser.models.agent import AgentRequest


@dataclass
class BenchmarkCase:
    case_id: str
    prompt: str
    context_summary: str | None = None
    expected_decision: str | None = None
    expected_page_intent: str | None = None
    max_results: int = 10
    max_sources: int = 5


@dataclass
class PlannerBenchmarkResult:
    case_id: str
    latency_ms: float
    decision: str
    page_intent: str
    expected_decision: str | None
    expected_page_intent: str | None
    decision_correct: bool | None
    page_intent_correct: bool | None


@dataclass
class WorkflowBenchmarkResult:
    case_id: str
    latency_ms: float
    decision: str
    page_intent: str
    synthesis_mode: str | None
    section_count: int
    citation_count: int
    related_link_count: int


def load_benchmark_cases(path: str | Path) -> list[BenchmarkCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Benchmark case file must contain a JSON array.")
    return [BenchmarkCase(**item) for item in payload]


def summarize_planner_results(results: Iterable[PlannerBenchmarkResult]) -> dict:
    rows = list(results)
    decision_cases = [row for row in rows if row.decision_correct is not None]
    intent_cases = [row for row in rows if row.page_intent_correct is not None]
    return {
        "cases": len(rows),
        "decision_accuracy": (
            sum(1 for row in decision_cases if row.decision_correct) / len(decision_cases)
            if decision_cases
            else None
        ),
        "intent_accuracy": (
            sum(1 for row in intent_cases if row.page_intent_correct) / len(intent_cases)
            if intent_cases
            else None
        ),
        "avg_latency_ms": (sum(row.latency_ms for row in rows) / len(rows)) if rows else 0.0,
    }


def summarize_workflow_results(results: Iterable[WorkflowBenchmarkResult]) -> dict:
    rows = list(results)
    fallback_cases = [row for row in rows if row.synthesis_mode == "deterministic"]
    return {
        "cases": len(rows),
        "avg_latency_ms": (sum(row.latency_ms for row in rows) / len(rows)) if rows else 0.0,
        "fallback_rate": (len(fallback_cases) / len(rows)) if rows else 0.0,
        "avg_sections": (sum(row.section_count for row in rows) / len(rows)) if rows else 0.0,
        "avg_citations": (sum(row.citation_count for row in rows) / len(rows)) if rows else 0.0,
    }


async def run_planner_benchmarks(
    cases: Iterable[BenchmarkCase],
    planner: Optional[AgentPlanner] = None,
) -> dict:
    runner = planner or get_agent_planner()
    results: list[PlannerBenchmarkResult] = []

    for case in cases:
        request = AgentRequest(
            prompt=case.prompt,
            context_summary=case.context_summary,
            max_results=case.max_results,
            max_sources=case.max_sources,
        )
        started = perf_counter()
        output = runner.plan(request)
        output = await output if asyncio.iscoroutine(output) else output
        latency_ms = (perf_counter() - started) * 1000
        results.append(
            PlannerBenchmarkResult(
                case_id=case.case_id,
                latency_ms=round(latency_ms, 2),
                decision=output.decision.value,
                page_intent=output.page_intent.value,
                expected_decision=case.expected_decision,
                expected_page_intent=case.expected_page_intent,
                decision_correct=(
                    output.decision.value == case.expected_decision
                    if case.expected_decision is not None
                    else None
                ),
                page_intent_correct=(
                    output.page_intent.value == case.expected_page_intent
                    if case.expected_page_intent is not None
                    else None
                ),
            )
        )

    return {
        "mode": "planner",
        "summary": summarize_planner_results(results),
        "results": [asdict(result) for result in results],
    }


async def run_workflow_benchmarks(
    cases: Iterable[BenchmarkCase],
    workflow: Optional[AgentWorkflow] = None,
) -> dict:
    runner = workflow or get_agent_workflow()
    results: list[WorkflowBenchmarkResult] = []

    for case in cases:
        request = AgentRequest(
            prompt=case.prompt,
            context_summary=case.context_summary,
            max_results=case.max_results,
            max_sources=case.max_sources,
        )
        started = perf_counter()
        response = await runner.run(request)
        latency_ms = (perf_counter() - started) * 1000
        results.append(
            WorkflowBenchmarkResult(
                case_id=case.case_id,
                latency_ms=round(latency_ms, 2),
                decision=response.planner.decision.value,
                page_intent=response.planner.page_intent.value,
                synthesis_mode=response.page.synthesis_mode,
                section_count=len(response.page.sections),
                citation_count=len(response.page.citations),
                related_link_count=len(response.page.related_links),
            )
        )

    return {
        "mode": "workflow",
        "summary": summarize_workflow_results(results),
        "results": [asdict(result) for result in results],
    }

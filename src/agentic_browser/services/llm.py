from __future__ import annotations

import json
from dataclasses import dataclass
import logging

import httpx

from agentic_browser.config import Settings, get_settings
from agentic_browser.models.agent import AgentRequest, PlannerOutput


logger = logging.getLogger("uvicorn.error")

PLANNER_SYSTEM_PROMPT = """
You are the planner for an agentic browser that answers user requests by generating a webpage for a blog-style browsing experience.

Your job is not to write the webpage. Your job is to decide the best information-gathering action so downstream steps can build a clear, useful, source-grounded page.

The generated page should feel like a concise, navigable blog article:
- organized around a coherent topic
- grounded in either current page context or retrieved sources
- suitable for headings, sections, citations, and related links
- focused on helping the user explore, compare, summarize, or go deeper

You must choose one decision:
- answer_from_context: use this only when the current context_summary is sufficient to produce a useful webpage without new retrieval
- search_web: use this when the request needs external information or source grounding
- refine_and_search: use this when the request is broad, complex, ambiguous, or would benefit from better-framed search queries before retrieval
- navigate_deeper: use this when the user is clearly drilling further into the current page/topic and retrieval should continue in that direction

Decision guidance:
- Prefer answer_from_context only when the existing context is enough for a meaningful page, not just a partial answer
- Prefer search when the user asks for fresh facts, comparisons, examples, recent developments, external validation, or anything not safely contained in the current context
- Prefer refine_and_search when better phrasing will improve retrieval quality
- Prefer navigate_deeper when the user wants more depth, more detail, or continuation from the current topic or target URL

Search query guidance:
- If the decision uses search, provide one or more concrete search queries
- Queries should be short, specific, and optimized for web retrieval
- Avoid conversational filler
- Preserve important entities, products, people, dates, and comparison targets
- If the request is about recent or latest information, include that intent in the query

Output rules:
- Return only JSON
- Use exactly these keys: decision, reasoning, search_queries, source_limit
- Allowed decision values are: answer_from_context, search_web, refine_and_search, navigate_deeper
- If decision is answer_from_context, search_queries must be an empty array
- If decision uses search, search_queries must contain at least one query
- reasoning should be brief and explain why this action best supports building the webpage
- Keep source_limit between 1 and 5
""".strip()


class PlannerServiceError(Exception):
    """Raised when the planner LLM cannot produce a valid response."""


@dataclass
class AzureAIPlannerService:
    settings: Settings

    def is_configured(self) -> bool:
        return all(
            (
                self.settings.azure_openai_endpoint,
                self.settings.azure_openai_api_key,
                self.settings.azure_openai_deployment_name,
                self.settings.azure_openai_api_version,
            )
        )

    async def plan(self, request: AgentRequest) -> PlannerOutput:
        if not self.is_configured():
            raise PlannerServiceError("Azure AI Foundry planner is not configured.")

        payload = self._build_payload(request)
        endpoint = (
            f"{self.settings.azure_openai_endpoint.rstrip('/')}"
            f"/openai/deployments/{self.settings.azure_openai_deployment_name}/chat/completions"
        )
        headers = {
            "api-key": self.settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }
        params = {"api-version": self.settings.azure_openai_api_version}

        async with httpx.AsyncClient(timeout=self.settings.azure_openai_timeout_seconds) as client:
            response = await client.post(endpoint, params=params, headers=headers, json=payload)
            response.raise_for_status()

        response_payload = response.json()
        logger.info(
            "Azure AI Foundry planner response received deployment=%s status=%s",
            self.settings.azure_openai_deployment_name,
            response.status_code,
        )
        logger.debug(
            "Azure AI Foundry planner raw response deployment=%s payload=%s",
            self.settings.azure_openai_deployment_name,
            json.dumps(response_payload),
        )
        return self._parse_response(request, response_payload)

    def _build_payload(self, request: AgentRequest) -> dict:
        return {
            "messages": [
                {
                    "role": "system",
                    "content": PLANNER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": request.prompt,
                            "context_summary": request.context_summary,
                            "session_id": request.session_id,
                            "current_page_id": request.current_page_id,
                            "navigation_target_url": request.navigation_target_url,
                            "max_sources": request.max_sources,
                            "max_results": request.max_results,
                        }
                    ),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

    def _parse_response(self, request: AgentRequest, payload: dict) -> PlannerOutput:
        try:
            content = payload["choices"][0]["message"]["content"]
            raw = json.loads(content)
            raw["source_limit"] = min(int(raw.get("source_limit", request.max_sources)), request.max_sources, 5)
            planner_output = PlannerOutput.model_validate(raw)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PlannerServiceError("Planner LLM returned an invalid response payload.") from exc

        if planner_output.decision.value != "answer_from_context" and not planner_output.search_queries:
            raise PlannerServiceError("Planner LLM returned a search decision without search queries.")

        return planner_output


def get_planner_service() -> AzureAIPlannerService:
    return AzureAIPlannerService(settings=get_settings())

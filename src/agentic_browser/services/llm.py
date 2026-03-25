from __future__ import annotations

import json
from dataclasses import dataclass
import logging
from typing import Iterable

import httpx

from agentic_browser.config import Settings, get_settings
from agentic_browser.models.agent import AgentRequest, ExtractedSource, PageIntent, PlannerOutput
from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage
from agentic_browser.models.search import SearchResult


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
- Use exactly these keys: decision, reasoning, page_intent, search_queries, source_limit
- Allowed decision values are: answer_from_context, search_web, refine_and_search, navigate_deeper
- Allowed page_intent values are: overview, review, recipe, how_to, comparison
- If decision is answer_from_context, search_queries must be an empty array
- If decision uses search, search_queries must contain at least one query
- reasoning should be brief and explain why this action best supports building the webpage
- Keep source_limit between 1 and 5
""".strip()

SYNTHESIS_SYSTEM_PROMPT = """
You are the structured synthesis node for an agentic browser that generates webpage-ready content for a blog-style browsing experience.

Your job is to convert the user's prompt, current context, and extracted source evidence into a bounded page contract that the application will render.

The resulting page should:
- feel like a concise, useful blog article rather than a chat response
- be grounded in the supplied context and extracted sources
- organize information into a clear title, hero summary, sections, citations, and optional source-grounded related links
- remain safe for deterministic rendering by returning only JSON

General synthesis rules:
- build the page around the user's task, not around the source list
- do not create one section per source unless that is clearly the best structure for the request
- merge compatible evidence across sources into coherent sections
- choose section titles that fit the task, such as overview, ingredients, method, comparison points, recommendations, caveats, or next steps
- use extracted headings and list items as clues for the section structure commonly present in the sources
- the page should feel complete and useful on its own, not like a loose summary of search results

If the planner says the page_intent is recipe:
- synthesize a single coherent recipe page, not a source-by-source roundup
- choose one primary recipe when multiple recipes disagree
- use supporting sources only for tips, variations, or source notes
- prefer sections such as Ingredients, Method, Tips and Variations, and Source Notes
- make the page complete enough for someone to actually follow the recipe

If the planner says the page_intent is review:
- synthesize a coherent review page, not a source-by-source roundup
- organize the page around the aspects the user cares about, such as design, performance, price and value, audience fit, pros and cons, and verdict
- prefer balanced language grounded in the supplied evidence
- make it easy for a reader to understand who the product is for and whether it seems worth buying

Return only JSON with these keys:
- title
- hero_summary
- sections
- citations
- related_links
- hero_image_url
- theme_hints
- context_summary

Section rules:
- Provide 1 to 4 sections
- Each section must contain: title, body, bullets, citations
- Keep section bodies concise and webpage-friendly
- Use citations only from the supplied source URLs/citations

Evidence rules:
- Do not invent facts, citations, or links
- If evidence is weak, summarize conservatively
- Prefer source-grounded phrasing over speculation

Image and style rules:
- hero_image_url must be one of the provided candidate image URLs or null
- theme_hints should stay minimal and only include grounded values such as theme_color when supported by the sources

Related-link rules:
- Only use the provided selected source URLs if you emit related_links
- related_links must be an array of objects, not an array of strings
- each related_links item must contain: label, url, snippet, follow_up_prompt
- It is acceptable to return an empty related_links array if you are unsure

Context-summary rules:
- context_summary should be a short summary suitable for future follow-up navigation
- It can be similar to hero_summary but should stay concise
""".strip()


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _build_default_related_links(selected_sources: list[SearchResult]) -> list[RelatedLink]:
    return [
        RelatedLink(
            label=source.title,
            url=source.url,
            snippet=source.snippet,
            follow_up_prompt=f"Tell me more about {source.title}",
        )
        for source in selected_sources[:5]
    ]


def _source_citations(source: ExtractedSource) -> list[str]:
    return source.citations or [source.url]


def _sentence_bullets(text: str, limit: int = 5) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    bullets = [
        sentence.strip(" -")
        for sentence in normalized.replace("?", ".").replace("!", ".").split(".")
        if sentence.strip()
    ]
    return bullets[:limit]


def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in keywords)


def _collect_review_evidence(extracted_sources: list[ExtractedSource], keywords: tuple[str, ...], limit: int = 6) -> list[str]:
    evidence = _dedupe_preserve_order(
        bullet
        for source in extracted_sources[:5]
        for bullet in (
            source.list_items
            + source.headings[1:]
            + _sentence_bullets(source.content_preview or source.snippet, limit=4)
        )
        if _matches_any(bullet, keywords)
    )
    return evidence[:limit]


def _requested_review_sections(prompt: str) -> list[tuple[str, tuple[str, ...], str]]:
    prompt_lower = prompt.lower()
    aspect_definitions = [
        ("Design and Everyday Use", ("design", "build", "display", "keyboard", "trackpad", "portable", "travel", "thin"), "This section covers the design, build, and day-to-day experience."),
        ("Performance", ("performance", "speed", "chip", "battery", "fast", "graphics", "benchmark"), "This section summarizes speed, battery, and overall capability."),
        ("Price and Value", ("price", "value", "cost", "worth", "money", "expensive", "cheap", "$"), "This section evaluates pricing and value for money."),
        ("Who This Is For", ("who", "for", "student", "creator", "office", "travel", "everyday", "workflows"), "This section helps the reader judge whether the product fits their needs."),
        ("Pros and Cons", ("pros", "cons", "advantages", "disadvantages", "tradeoffs"), "This section summarizes the biggest strengths and tradeoffs."),
        ("Verdict", ("verdict", "should you buy", "recommend", "worth it"), "This section gives the overall buying recommendation."),
    ]
    requested = [definition for definition in aspect_definitions if any(keyword in prompt_lower for keyword in definition[1])]
    if requested:
        return requested[:4]
    return aspect_definitions[:4]


def _sanitize_theme_hints(theme_hints: dict[str, str]) -> dict[str, str]:
    sanitized = {
        key: value
        for key, value in theme_hints.items()
        if isinstance(value, str) and value
    }
    theme_color = sanitized.get("theme_color", "").strip().lower()
    if theme_color in {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgba(255,255,255,1)", "rgba(255, 255, 255, 1)"}:
        sanitized.pop("theme_color", None)
    return sanitized


def _normalize_related_links(raw_related_links: object, selected_sources: list[SearchResult]) -> list[dict]:
    if not isinstance(raw_related_links, list):
        return []

    selected_by_url = {source.url: source for source in selected_sources}
    normalized: list[dict] = []

    for item in raw_related_links:
        if isinstance(item, str):
            source = selected_by_url.get(item)
            if source is None:
                continue
            normalized.append(
                {
                    "label": source.title,
                    "url": source.url,
                    "snippet": source.snippet,
                    "follow_up_prompt": f"Tell me more about {source.title}",
                }
            )
            continue

        if isinstance(item, dict):
            normalized.append(item)

    return normalized


def _ensure_intent_sections(
    request: AgentRequest,
    planner: PlannerOutput,
    sections: list[PageSection],
    extracted_sources: list[ExtractedSource],
    citations: list[str],
) -> list[PageSection]:
    normalized_sections = list(sections)

    if planner.page_intent == PageIntent.RECIPE:
        recipe_primary = max(
            extracted_sources,
            key=lambda source: (len(source.recipe_ingredients), len(source.recipe_steps), len(source.content_preview)),
            default=None,
        )
        if recipe_primary and (recipe_primary.recipe_ingredients or recipe_primary.recipe_steps):
            if not any(section.title.lower() == "ingredients" for section in normalized_sections) and recipe_primary.recipe_ingredients:
                normalized_sections.insert(
                    0,
                    PageSection(
                        title="Ingredients",
                        body="Gather the ingredients below before you start.",
                        bullets=recipe_primary.recipe_ingredients[:12],
                        citations=_source_citations(recipe_primary),
                    ),
                )
            if not any(section.title.lower() == "method" for section in normalized_sections) and recipe_primary.recipe_steps:
                normalized_sections.insert(
                    1 if normalized_sections else 0,
                    PageSection(
                        title="Method",
                        body="Follow these steps to make the recipe.",
                        bullets=recipe_primary.recipe_steps[:8],
                        citations=_source_citations(recipe_primary),
                    ),
                )
            if not any("tip" in section.title.lower() or "variation" in section.title.lower() for section in normalized_sections):
                recipe_notes = _dedupe_preserve_order(note for source in extracted_sources for note in source.recipe_notes)
                if recipe_notes:
                    normalized_sections.append(
                        PageSection(
                            title="Tips and Variations",
                            body="Use these notes and variations to adapt the recipe.",
                            bullets=recipe_notes[:8],
                            citations=citations[:3],
                        )
                    )
        return normalized_sections[:4]

    if not extracted_sources:
        return normalized_sections[:4]

    if planner.page_intent == PageIntent.HOW_TO:
        if not any("step" in section.title.lower() for section in normalized_sections):
            primary = extracted_sources[0]
            normalized_sections.insert(
                0,
                PageSection(
                    title="Steps",
                    body="Follow this sequence to complete the task.",
                    bullets=_sentence_bullets(primary.content_preview or primary.snippet, limit=6) or primary.headings[:4],
                    citations=_source_citations(primary),
                ),
            )
        if not any("need" in section.title.lower() or "prepare" in section.title.lower() for section in normalized_sections):
            prep_bullets = _dedupe_preserve_order(
                heading for source in extracted_sources[:3] for heading in source.headings[1:4]
            )[:6]
            if prep_bullets:
                normalized_sections.insert(
                    0,
                    PageSection(
                        title="What You'll Need",
                        body="Start by gathering the prerequisites, tools, or context referenced by the sources.",
                        bullets=prep_bullets,
                        citations=citations[:3],
                    ),
                )
        return normalized_sections[:4]

    if planner.page_intent == PageIntent.REVIEW:
        review_templates = [
            (title, body, _collect_review_evidence(extracted_sources, keywords))
            for title, keywords, body in _requested_review_sections(request.prompt)
        ]
        for title, body, bullets in reversed(review_templates):
            if bullets and not any(section.title.lower() == title.lower() for section in normalized_sections):
                normalized_sections.insert(
                    0,
                    PageSection(
                        title=title,
                        body=body,
                        bullets=bullets,
                        citations=citations[:3],
                    ),
                )
        if not normalized_sections:
            primary = extracted_sources[0]
            normalized_sections = [
                PageSection(
                    title="Verdict",
                    body=primary.content_preview or primary.snippet,
                    bullets=_sentence_bullets(primary.content_preview or primary.snippet, limit=4),
                    citations=_source_citations(primary),
                )
            ]
        return normalized_sections[:4]

    if planner.page_intent == PageIntent.COMPARISON:
        if not any("difference" in section.title.lower() or "compare" in section.title.lower() for section in normalized_sections):
            differences = _dedupe_preserve_order(
                bullet
                for source in extracted_sources[:3]
                for bullet in _sentence_bullets(source.content_preview or source.snippet, limit=2)
            )[:8]
            if differences:
                normalized_sections.insert(
                    0,
                    PageSection(
                        title="Key Differences",
                        body="Compare the main tradeoffs and distinguishing details across the sources.",
                        bullets=differences,
                        citations=citations[:3],
                    ),
                )
        return normalized_sections[:4]

    if planner.page_intent == PageIntent.OVERVIEW and not any(section.title.lower() == "overview" for section in normalized_sections):
        primary = extracted_sources[0]
        normalized_sections.insert(
            0,
            PageSection(
                title="Overview",
                body=primary.content_preview or primary.snippet,
                bullets=_sentence_bullets(primary.content_preview or primary.snippet, limit=4),
                citations=_source_citations(primary),
            ),
        )

    return normalized_sections[:4]


class PlannerServiceError(Exception):
    """Raised when the planner LLM cannot produce a valid response."""


class SynthesisServiceError(Exception):
    """Raised when the synthesis LLM cannot produce a valid page."""


def _decode_response_json(response: httpx.Response, error_cls: type[Exception], message: str) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise error_cls(message) from exc
    if not isinstance(payload, dict):
        raise error_cls(message)
    return payload


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

        response_payload = _decode_response_json(
            response,
            PlannerServiceError,
            "Planner LLM returned a non-JSON response payload.",
        )
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


@dataclass
class AzureAISynthesisService:
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

    async def synthesize(
        self,
        request: AgentRequest,
        planner: PlannerOutput,
        extracted_sources: list[ExtractedSource],
        selected_sources: list[SearchResult],
    ) -> SynthesizedPage:
        if not self.is_configured():
            raise SynthesisServiceError("Azure AI Foundry synthesis is not configured.")

        payload = self._build_payload(request, planner, extracted_sources, selected_sources)
        endpoint = (
            f"{self.settings.azure_openai_endpoint.rstrip('/')}"
            f"/openai/deployments/{self.settings.azure_openai_deployment_name}/chat/completions"
        )
        headers = {
            "api-key": self.settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }
        params = {"api-version": self.settings.azure_openai_api_version}

        async with httpx.AsyncClient(timeout=self.settings.azure_openai_synthesis_timeout_seconds) as client:
            response = await client.post(endpoint, params=params, headers=headers, json=payload)
            response.raise_for_status()

        response_payload = _decode_response_json(
            response,
            SynthesisServiceError,
            "Synthesis LLM returned a non-JSON response payload.",
        )
        logger.info(
            "Azure AI Foundry synthesis response received deployment=%s status=%s",
            self.settings.azure_openai_deployment_name,
            response.status_code,
        )
        logger.debug(
            "Azure AI Foundry synthesis raw response deployment=%s payload=%s",
            self.settings.azure_openai_deployment_name,
            json.dumps(response_payload),
        )
        return self._parse_response(request, planner, response_payload, extracted_sources, selected_sources)

    def _build_payload(
        self,
        request: AgentRequest,
        planner: PlannerOutput,
        extracted_sources: list[ExtractedSource],
        selected_sources: list[SearchResult],
    ) -> dict:
        candidate_images = _dedupe_preserve_order(
            image_url
            for source in extracted_sources
            for image_url in source.image_urls
        )
        source_theme_colors = _dedupe_preserve_order(
            source.style_hints.get("theme_color", "")
            for source in extracted_sources
            if source.style_hints
        )
        return {
            "messages": [
                {
                    "role": "system",
                    "content": SYNTHESIS_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": request.prompt,
                            "planner_decision": planner.decision.value,
                            "page_intent": planner.page_intent.value,
                            "planner_reasoning": planner.reasoning,
                            "context_summary": request.context_summary,
                            "navigation_target_url": request.navigation_target_url,
                            "selected_sources": [
                                {
                                    "title": source.title,
                                    "url": source.url,
                                    "snippet": source.snippet,
                                }
                                for source in selected_sources[:5]
                            ],
                            "extracted_sources": [
                                {
                                    "title": source.title,
                                    "url": source.url,
                                    "snippet": source.snippet,
                                     "content_preview": source.content_preview,
                                     "headings": source.headings[:5],
                                     "list_items": source.list_items[:12],
                                     "citations": source.citations[:5],
                                    "image_urls": source.image_urls[:5],
                                    "style_hints": source.style_hints,
                                    "recipe_ingredients": source.recipe_ingredients[:15],
                                    "recipe_steps": source.recipe_steps[:12],
                                    "recipe_notes": source.recipe_notes[:8],
                                }
                                for source in extracted_sources[:5]
                            ],
                            "candidate_image_urls": candidate_images[:10],
                            "candidate_theme_colors": source_theme_colors[:5],
                        }
                    ),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

    def _parse_response(
        self,
        request: AgentRequest,
        planner: PlannerOutput,
        payload: dict,
        extracted_sources: list[ExtractedSource],
        selected_sources: list[SearchResult],
    ) -> SynthesizedPage:
        try:
            content = payload["choices"][0]["message"]["content"]
            raw = json.loads(content)
            raw["sections"] = raw.get("sections") if isinstance(raw.get("sections"), list) else []
            raw["citations"] = raw.get("citations") if isinstance(raw.get("citations"), list) else []
            raw["related_links"] = _normalize_related_links(raw.get("related_links"), selected_sources)
            raw["theme_hints"] = raw.get("theme_hints") if isinstance(raw.get("theme_hints"), dict) else {}
            for section in raw["sections"]:
                if not isinstance(section, dict):
                    continue
                section["bullets"] = section.get("bullets") if isinstance(section.get("bullets"), list) else []
                section["citations"] = section.get("citations") if isinstance(section.get("citations"), list) else []
            page = SynthesizedPage.model_validate(raw)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SynthesisServiceError("Synthesis LLM returned an invalid response payload.") from exc

        allowed_citations = set(
            _dedupe_preserve_order(
                citation
                for source in extracted_sources
                for citation in (source.citations or [source.url])
            )
        )
        allowed_related_urls = {source.url for source in selected_sources}
        allowed_image_urls = set(
            _dedupe_preserve_order(
                image_url
                for source in extracted_sources
                for image_url in source.image_urls
            )
        )
        fallback_theme_hints = next(
            (source.style_hints for source in extracted_sources if source.style_hints),
            {},
        )

        sections = [
            section.model_copy(
                update={
                    "citations": [
                        citation
                        for citation in _dedupe_preserve_order(section.citations)
                        if citation in allowed_citations
                    ]
                }
            )
            for section in page.sections[:4]
        ]
        citations = [
            citation
            for citation in _dedupe_preserve_order(page.citations)
            if citation in allowed_citations
        ]
        related_links = [
            link
            for link in page.related_links
            if link.url in allowed_related_urls
        ]
        if not related_links:
            related_links = _build_default_related_links(selected_sources)

        hero_image_url = page.hero_image_url if page.hero_image_url in allowed_image_urls else None
        theme_hints = _sanitize_theme_hints(page.theme_hints)
        if not theme_hints and fallback_theme_hints:
            theme_hints = _sanitize_theme_hints(fallback_theme_hints)

        sections = _ensure_intent_sections(request, planner, sections, extracted_sources, citations)

        context_summary = page.context_summary or page.hero_summary
        if not sections:
            sections = [
                PageSection(
                    title="Summary",
                    body=page.hero_summary,
                    citations=citations,
                )
            ]

        return page.model_copy(
            update={
                "sections": sections,
                "citations": citations,
                "related_links": related_links,
                "hero_image_url": hero_image_url,
                "theme_hints": theme_hints,
                "context_summary": context_summary,
                "synthesis_mode": "llm",
                "synthesis_note": "Rendered using Azure AI synthesis.",
            }
        )


def get_synthesis_service() -> AzureAISynthesisService:
    return AzureAISynthesisService(settings=get_settings())

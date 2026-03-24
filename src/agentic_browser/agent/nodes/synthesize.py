from __future__ import annotations

import logging

from agentic_browser.agent.state import AgentGraphState
from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage

logger = logging.getLogger("uvicorn.error")


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def synthesize_page_node(state: AgentGraphState) -> AgentGraphState:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    selected_sources = state.get("selected_sources", [])
    planner = state["planner"]

    if extracted_sources:
        title = extracted_sources[0].headings[0] if extracted_sources[0].headings else extracted_sources[0].title
        hero_summary = " ".join(
            source.content_preview.strip()
            for source in extracted_sources[:2]
            if source.content_preview.strip()
        )[:400]
        if not hero_summary:
            hero_summary = f"Synthesized results for: {request.prompt}"

        sections = [
            PageSection(
                title=source.headings[0] if source.headings else source.title,
                body=source.content_preview or source.snippet,
                bullets=source.headings[1:4],
                citations=source.citations or [source.url],
            )
            for source in extracted_sources[:3]
        ]

        citations = _dedupe_preserve_order(
            [
                citation
                for source in extracted_sources
                for citation in (source.citations or [source.url])
            ]
        )
        hero_image_url = next(
            (source.image_urls[0] for source in extracted_sources if source.image_urls),
            None,
        )
        theme_hints = next(
            (source.style_hints for source in extracted_sources if source.style_hints),
            {},
        )
    else:
        title = request.prompt.strip().rstrip("?.!") or "Generated Page"
        hero_summary = (
            request.context_summary
            or "The planner answered from the current context without web retrieval."
        )
        sections = [
            PageSection(
                title="Current context",
                body=hero_summary,
                citations=[],
            )
        ]
        citations = []
        hero_image_url = None
        theme_hints = {}

    related_links = [
        RelatedLink(
            label=source.title,
            url=source.url,
            snippet=source.snippet,
            follow_up_prompt=f"Tell me more about {source.title}",
        )
        for source in selected_sources[:5]
    ]

    page = SynthesizedPage(
        title=title,
        hero_summary=hero_summary,
        sections=sections,
        citations=citations,
        related_links=related_links,
        hero_image_url=hero_image_url,
        theme_hints=theme_hints,
        context_summary=hero_summary,
    )
    logger.info(
        "Synthesis produced page prompt=%r sections=%s citations=%s related_links=%s decision=%s",
        request.prompt,
        len(page.sections),
        len(page.citations),
        len(page.related_links),
        planner.decision.value,
    )
    return {"page": page}

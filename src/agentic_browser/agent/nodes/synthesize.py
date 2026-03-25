from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Awaitable, Protocol, Union

import httpx

from agentic_browser.agent.state import AgentGraphState
from agentic_browser.models.agent import ExtractedSource, PageIntent, PlannerOutput
from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage
from agentic_browser.services.llm import (
    AzureAISynthesisService,
    SynthesisServiceError,
    get_synthesis_service,
)

logger = logging.getLogger("uvicorn.error")


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _source_citations(source: ExtractedSource) -> list[str]:
    return source.citations or [source.url]


def _collect_citations(extracted_sources: list[ExtractedSource]) -> list[str]:
    return _dedupe_preserve_order(
        [
            citation
            for source in extracted_sources
            for citation in _source_citations(source)
        ]
    )


def _collect_theme_hints(extracted_sources: list[ExtractedSource]) -> dict[str, str]:
    theme_hints = next((source.style_hints for source in extracted_sources if source.style_hints), {})
    theme_color = theme_hints.get("theme_color", "").strip().lower()
    if theme_color in {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgba(255,255,255,1)", "rgba(255, 255, 255, 1)"}:
        sanitized = dict(theme_hints)
        sanitized.pop("theme_color", None)
        return sanitized
    return theme_hints


def _collect_hero_image(extracted_sources: list[ExtractedSource]) -> str | None:
    return next((source.image_urls[0] for source in extracted_sources if source.image_urls), None)


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


def _source_structure_bullets(source: ExtractedSource, limit: int = 6) -> list[str]:
    return _dedupe_preserve_order(source.list_items + source.headings[1:])[:limit]


def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in keywords)


def _with_synthesis_metadata(page: SynthesizedPage, mode: str, note: str | None = None) -> SynthesizedPage:
    return page.model_copy(update={"synthesis_mode": mode, "synthesis_note": note})


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


def _requested_how_to_sections(prompt: str) -> list[str]:
    prompt_lower = prompt.lower()
    section_order = ["What You'll Need", "Steps", "Verify Installation", "Next Steps"]
    if any(term in prompt_lower for term in ("install", "setup", "set up", "download")):
        return section_order
    return ["What You'll Need", "Steps", "Next Steps"]


def _is_noisy_heading(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"tech", "reviews", "science", "video", "videos", "youtube"}


def _is_actionable_step(value: str) -> bool:
    normalized = value.strip().lower()
    return len(normalized.split()) >= 3 and not _is_noisy_heading(normalized)


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


def _section(title: str, body: str, bullets: list[str], citations: list[str]) -> PageSection:
    return PageSection(
        title=title,
        body=body,
        bullets=_dedupe_preserve_order([bullet for bullet in bullets if bullet])[:8],
        citations=_dedupe_preserve_order([citation for citation in citations if citation])[:5],
    )


def _build_related_links(state: AgentGraphState) -> list[RelatedLink]:
    selected_sources = state.get("selected_sources", [])
    return [
        RelatedLink(
            label=source.title,
            url=source.url,
            snippet=source.snippet,
            follow_up_prompt=f"Tell me more about {source.title}",
        )
        for source in selected_sources[:5]
    ]


def _recipe_primary_source(state: AgentGraphState):
    extracted_sources = state.get("extracted_sources", [])
    ranked_sources = sorted(
        extracted_sources,
        key=lambda source: (len(source.recipe_ingredients), len(source.recipe_steps), len(source.content_preview)),
        reverse=True,
    )
    return ranked_sources[0] if ranked_sources and (ranked_sources[0].recipe_ingredients or ranked_sources[0].recipe_steps) else None


def _build_recipe_page(state: AgentGraphState) -> SynthesizedPage | None:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    primary_source = _recipe_primary_source(state)
    if primary_source is None:
        return None

    citations = _collect_citations(extracted_sources)
    hero_image_url = _collect_hero_image(extracted_sources)
    theme_hints = _collect_theme_hints(extracted_sources)

    ingredient_section = PageSection(
        title="Ingredients",
        body="Gather the ingredients below before you start blending.",
        bullets=primary_source.recipe_ingredients[:12],
        citations=_source_citations(primary_source),
    )
    method_bullets = primary_source.recipe_steps[:8]
    method_body = (
        "Follow these steps to make the recipe."
        if method_bullets
        else primary_source.content_preview or primary_source.snippet
    )
    method_section = PageSection(
        title="Method",
        body=method_body,
        bullets=method_bullets,
        citations=_source_citations(primary_source),
    )

    supporting_notes = _dedupe_preserve_order(
        note
        for source in extracted_sources
        for note in source.recipe_notes
    )
    variation_bullets = _dedupe_preserve_order(
        bullet
        for source in extracted_sources[1:]
        for bullet in source.recipe_ingredients[:4]
    )[:8]
    tips_section = PageSection(
        title="Tips and Variations",
        body="Use these notes and alternate ingredient ideas to adapt the recipe.",
        bullets=(supporting_notes + variation_bullets)[:8],
        citations=citations[:3],
    )

    sections = [ingredient_section, method_section]
    if tips_section.bullets:
        sections.append(tips_section)

    hero_summary = primary_source.content_preview or primary_source.snippet or f"Recipe for {request.prompt}"
    return SynthesizedPage(
        title=primary_source.title,
        hero_summary=hero_summary[:400],
        sections=sections,
        citations=citations,
        related_links=_build_related_links(state),
        hero_image_url=hero_image_url,
        theme_hints=theme_hints,
        context_summary=hero_summary[:400],
    )


def _build_review_page(state: AgentGraphState) -> SynthesizedPage | None:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    if not extracted_sources:
        return None

    primary_source = extracted_sources[0]
    citations = _collect_citations(extracted_sources)
    hero_summary = " ".join(
        (source.content_preview or source.snippet).strip()
        for source in extracted_sources[:2]
        if (source.content_preview or source.snippet).strip()
    )[:400]
    if not hero_summary:
        hero_summary = f"Review for {request.prompt}"

    verdict_points = _dedupe_preserve_order(
        f"{source.title}: {(source.snippet or source.content_preview)[:120].strip()}"
        for source in extracted_sources[:4]
    )[:5]

    sections: list[PageSection] = []
    for title, keywords, body in _requested_review_sections(request.prompt):
        bullets = _collect_review_evidence(extracted_sources, keywords)
        if title == "Design and Everyday Use":
            bullets = bullets or _source_structure_bullets(primary_source, limit=4)
        elif title == "Performance":
            bullets = bullets or _sentence_bullets(primary_source.content_preview or primary_source.snippet, limit=4)
        else:
            bullets = bullets or verdict_points[:4]
        sections.append(_section(title, body, bullets, citations[:3]))

    non_empty_sections = [section for section in sections if section.body or section.bullets]
    if verdict_points and len(non_empty_sections) < 4 and not any(section.title == "Verdict" for section in non_empty_sections):
        non_empty_sections.append(
            _section(
                "Verdict",
                "Taken together, the sources point to this overall buying recommendation.",
                verdict_points,
                citations[:3],
            )
        )

    return SynthesizedPage(
        title=primary_source.title if "review" in primary_source.title.lower() else f"Review: {primary_source.title}",
        hero_summary=hero_summary,
        sections=non_empty_sections[:4],
        citations=citations,
        related_links=_build_related_links(state),
        hero_image_url=_collect_hero_image(extracted_sources),
        theme_hints=_collect_theme_hints(extracted_sources),
        context_summary=hero_summary,
    )


def _build_overview_page(state: AgentGraphState) -> SynthesizedPage | None:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    if not extracted_sources:
        return None

    primary_source = extracted_sources[0]
    citations = _collect_citations(extracted_sources)
    summary_text = " ".join(
        source.content_preview.strip() or source.snippet.strip()
        for source in extracted_sources[:3]
        if (source.content_preview or source.snippet).strip()
    )[:400]
    if not summary_text:
        summary_text = f"Overview for {request.prompt}"

    key_points = _dedupe_preserve_order(
        bullet
        for source in extracted_sources[:3]
        for bullet in (
            _source_structure_bullets(source, limit=3)
            or _sentence_bullets(source.content_preview or source.snippet, limit=2)
        )
    )[:8]
    sources_bullets = _dedupe_preserve_order(
        f"{source.title}: {(source.snippet or source.content_preview)[:120].strip()}"
        for source in extracted_sources[:3]
    )[:5]

    sections = [
        _section(
            "Overview",
            summary_text,
            key_points[:4],
            citations[:3],
        )
    ]
    if key_points:
        sections.append(
            _section(
                "Key Points",
                "These are the main takeaways synthesized across the retrieved sources.",
                key_points,
                citations[:3],
            )
        )
    if len(extracted_sources) > 1:
        sections.append(
            _section(
                "Source Highlights",
                "These sources contributed the strongest evidence for this page.",
                sources_bullets,
                citations[: min(3, len(citations))],
            )
        )

    return SynthesizedPage(
        title=primary_source.headings[0] if primary_source.headings else primary_source.title,
        hero_summary=summary_text,
        sections=sections[:4],
        citations=citations,
        related_links=_build_related_links(state),
        hero_image_url=_collect_hero_image(extracted_sources),
        theme_hints=_collect_theme_hints(extracted_sources),
        context_summary=summary_text,
    )


def _build_how_to_page(state: AgentGraphState) -> SynthesizedPage | None:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    if not extracted_sources:
        return None

    primary_source = extracted_sources[0]
    citations = _collect_citations(extracted_sources)
    hero_summary = primary_source.content_preview or primary_source.snippet or f"Guide for {request.prompt}"
    preparation = _dedupe_preserve_order(
        heading
        for source in extracted_sources[:3]
        for heading in source.headings[1:4]
        if not _is_noisy_heading(heading)
    )[:6]
    steps = _dedupe_preserve_order(
        bullet
        for source in extracted_sources[:3]
        for bullet in (
            [item for item in source.list_items[:6] if _is_actionable_step(item)]
            or [item for item in _sentence_bullets(source.content_preview or source.snippet, limit=4) if _is_actionable_step(item)]
        )
    )[:8]
    verification = _dedupe_preserve_order(
        bullet
        for source in extracted_sources[:3]
        for bullet in _sentence_bullets(source.content_preview or source.snippet, limit=4)
        if _matches_any(bullet, ("open", "launch", "default", "verify", "success", "installed"))
    )[:6]
    next_steps = _dedupe_preserve_order(
        f"Review {source.title}" for source in extracted_sources[1:3]
    )[:4]

    sections: list[PageSection] = []
    for section_name in _requested_how_to_sections(request.prompt):
        if section_name == "What You'll Need":
            sections.append(
                _section(
                    "What You'll Need",
                    "Start by gathering the prerequisites, tools, or setup context before you begin.",
                    preparation or ["A MacBook with an internet connection", "A web browser such as Safari"],
                    citations[:3],
                )
            )
        elif section_name == "Steps":
            sections.append(
                _section(
                    "Steps",
                    "Follow the sequence below to work through the task.",
                    steps or _sentence_bullets(hero_summary, limit=4),
                    _source_citations(primary_source),
                )
            )
        elif section_name == "Verify Installation":
            verification_bullets = verification or ["Open the app and confirm it launches correctly."]
            sections.append(
                _section(
                    "Verify Installation",
                    "Use these checks to confirm the installation finished successfully.",
                    verification_bullets,
                    citations[:3],
                )
            )
        elif section_name == "Next Steps" and next_steps:
            sections.append(
                _section(
                    "Next Steps",
                    "Use these follow-up directions to go deeper once the main task is complete.",
                    next_steps,
                    citations[:3],
                )
            )

    return SynthesizedPage(
        title=primary_source.title,
        hero_summary=hero_summary[:400],
        sections=[section for section in sections if section.body or section.bullets][:4],
        citations=citations,
        related_links=_build_related_links(state),
        hero_image_url=_collect_hero_image(extracted_sources),
        theme_hints=_collect_theme_hints(extracted_sources),
        context_summary=hero_summary[:400],
    )


def _build_comparison_page(state: AgentGraphState) -> SynthesizedPage | None:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    if not extracted_sources:
        return None

    citations = _collect_citations(extracted_sources)
    options = _dedupe_preserve_order(source.title for source in extracted_sources[:4])
    differences = _dedupe_preserve_order(
        bullet
        for source in extracted_sources[:3]
        for bullet in (_source_structure_bullets(source, limit=2) or _sentence_bullets(source.content_preview or source.snippet, limit=2))
    )[:8]
    recommendations = _dedupe_preserve_order(
        f"Use {source.title} when {((source.snippet or source.content_preview)[:90]).strip()}"
        for source in extracted_sources[:3]
    )[:5]
    hero_summary = " ".join(
        (source.content_preview or source.snippet).strip()
        for source in extracted_sources[:2]
        if (source.content_preview or source.snippet).strip()
    )[:400]
    if not hero_summary:
        hero_summary = f"Comparison for {request.prompt}"

    sections = [
        _section(
            "Options Compared",
            "These are the main options or sources considered for the comparison.",
            options,
            citations[:3],
        ),
        _section(
            "Key Differences",
            "Compare the strengths, tradeoffs, and distinguishing details across the sources.",
            differences,
            citations[:3],
        ),
    ]
    if recommendations:
        sections.append(
            _section(
                "Recommendations",
                "Choose based on the scenario that best matches your goal.",
                recommendations,
                citations[:3],
            )
        )

    return SynthesizedPage(
        title=request.prompt.strip().rstrip("?.!") or "Comparison",
        hero_summary=hero_summary,
        sections=[section for section in sections if section.body or section.bullets][:4],
        citations=citations,
        related_links=_build_related_links(state),
        hero_image_url=_collect_hero_image(extracted_sources),
        theme_hints=_collect_theme_hints(extracted_sources),
        context_summary=hero_summary,
    )


def _build_intent_page(state: AgentGraphState) -> SynthesizedPage | None:
    planner = state["planner"]
    if planner.page_intent == PageIntent.REVIEW:
        return _build_review_page(state)
    if planner.page_intent == PageIntent.RECIPE:
        return _build_recipe_page(state)
    if planner.page_intent == PageIntent.HOW_TO:
        return _build_how_to_page(state)
    if planner.page_intent == PageIntent.COMPARISON:
        return _build_comparison_page(state)
    return _build_overview_page(state)


def build_deterministic_page(state: AgentGraphState) -> SynthesizedPage:
    request = state["request"]
    extracted_sources = state.get("extracted_sources", [])
    planner = state["planner"]

    intent_page = _build_intent_page(state)
    if intent_page is not None:
        logger.info(
            "Deterministic synthesis produced intent-shaped page prompt=%r intent=%s sections=%s citations=%s",
            request.prompt,
            planner.page_intent.value,
            len(intent_page.sections),
            len(intent_page.citations),
        )
        return _with_synthesis_metadata(
            intent_page,
            mode="deterministic",
            note="Rendered using deterministic fallback synthesis.",
        )

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

    related_links = _build_related_links(state)

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
    return _with_synthesis_metadata(
        page,
        mode="deterministic",
        note="Rendered using deterministic fallback synthesis.",
    )


class PageSynthesizer(Protocol):
    def synthesize(self, state: AgentGraphState) -> Union[SynthesizedPage, Awaitable[SynthesizedPage]]:
        ...


@dataclass
class DeterministicPageSynthesizer:
    def synthesize(self, state: AgentGraphState) -> SynthesizedPage:
        return build_deterministic_page(state)


@dataclass
class LlmPageSynthesizer:
    service: AzureAISynthesisService
    fallback: DeterministicPageSynthesizer

    async def synthesize(self, state: AgentGraphState) -> SynthesizedPage:
        request = state["request"]
        planner: PlannerOutput = state["planner"]
        extracted_sources = state.get("extracted_sources", [])
        selected_sources = state.get("selected_sources", [])
        deployment_name = getattr(getattr(self.service, "settings", None), "azure_openai_deployment_name", "unknown")
        try:
            logger.info(
                "Synthesis calling Azure AI Foundry deployment=%s prompt=%r extracted_sources=%s timeout_seconds=%s",
                deployment_name,
                request.prompt,
                len(extracted_sources),
                getattr(getattr(self.service, "settings", None), "azure_openai_synthesis_timeout_seconds", "unknown"),
            )
            page = await self.service.synthesize(
                request=request,
                planner=planner,
                extracted_sources=extracted_sources,
                selected_sources=selected_sources,
            )
            logger.info(
                "Synthesis using Azure AI Foundry deployment=%s sections=%s citations=%s related_links=%s",
                deployment_name,
                len(page.sections),
                len(page.citations),
                len(page.related_links),
            )
            return _with_synthesis_metadata(page, mode="llm", note="Rendered using Azure AI synthesis.")
        except SynthesisServiceError as exc:
            logger.warning("Synthesis LLM failed, falling back to deterministic synthesis: %s", exc)
            return self.fallback.synthesize(state)
        except httpx.HTTPError as exc:
            logger.warning(
                "Synthesis LLM HTTP failure, falling back to deterministic synthesis: %s (%r)",
                exc.__class__.__name__,
                exc,
            )
            return self.fallback.synthesize(state)


def synthesize_page_node(state: AgentGraphState) -> AgentGraphState:
    return {"page": build_deterministic_page(state)}


def get_page_synthesizer() -> PageSynthesizer:
    deterministic = DeterministicPageSynthesizer()
    service = get_synthesis_service()
    if not service.is_configured():
        logger.info("Synthesis initialized in deterministic mode because Azure AI Foundry is not fully configured")
        return deterministic
    logger.info(
        "Synthesis initialized in Azure AI Foundry mode deployment=%s",
        service.settings.azure_openai_deployment_name,
    )
    return LlmPageSynthesizer(service=service, fallback=deterministic)

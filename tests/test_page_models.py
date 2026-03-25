from agentic_browser.agent.nodes.synthesize import synthesize_page_node
from agentic_browser.models.agent import (
    AgentDecision,
    AgentRequest,
    ExtractedSource,
    PlannerOutput,
)
from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage


def test_synthesized_page_model_validates_nested_content() -> None:
    page = SynthesizedPage(
        title="Agentic Browser Overview",
        hero_summary="A structured page assembled from extracted evidence.",
        sections=[
            PageSection(
                title="Overview",
                body="Agentic browsers plan and retrieve before presenting results.",
                bullets=["Planner", "Retrieval", "Rendering"],
                citations=["https://example.com/overview"],
            )
        ],
        citations=["https://example.com/overview"],
        related_links=[
            RelatedLink(
                label="Example source",
                url="https://example.com/overview",
                snippet="Background reading",
                follow_up_prompt="Tell me more about Example source",
            )
        ],
        theme_hints={"theme_color": "#112233"},
        synthesis_mode="llm",
        synthesis_note="Rendered using Azure AI synthesis.",
        session_id="session-1",
        page_id="page-1",
        context_summary="A structured page assembled from extracted evidence.",
    )

    assert page.sections[0].title == "Overview"
    assert page.related_links[0].label == "Example source"
    assert page.related_links[0].follow_up_prompt == "Tell me more about Example source"
    assert page.theme_hints["theme_color"] == "#112233"
    assert page.synthesis_mode == "llm"
    assert page.synthesis_note == "Rendered using Azure AI synthesis."
    assert page.session_id == "session-1"
    assert page.page_id == "page-1"


def test_synthesis_citations_fall_back_per_source_url() -> None:
    state = {
        "request": AgentRequest(prompt="Explain agentic browsers"),
        "planner": PlannerOutput(
            decision=AgentDecision.SEARCH_WEB,
            reasoning="Search is needed.",
            search_queries=["Explain agentic browsers"],
            source_limit=2,
        ),
        "selected_sources": [],
        "extracted_sources": [
            ExtractedSource(
                title="Source A",
                url="https://example.com/a",
                snippet="A",
                content_preview="Content A",
                headings=["Overview A"],
                citations=["https://cite.example/a"],
                image_urls=[],
                style_hints={},
            ),
            ExtractedSource(
                title="Source B",
                url="https://example.com/b",
                snippet="B",
                content_preview="Content B",
                headings=["Overview B"],
                citations=[],
                image_urls=[],
                style_hints={},
            ),
        ],
    }

    result = synthesize_page_node(state)

    assert result["page"].citations == [
        "https://cite.example/a",
        "https://example.com/b",
    ]

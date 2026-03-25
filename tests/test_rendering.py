from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage
from agentic_browser.rendering.html import DeterministicHtmlRenderer


def test_renderer_outputs_structured_html_and_escapes_content() -> None:
    renderer = DeterministicHtmlRenderer(base_url="http://127.0.0.1:8000")
    page = SynthesizedPage(
        title='Agentic <Browser>',
        hero_summary='A "safe" summary',
        sections=[
            PageSection(
                title="Overview",
                body="Browsers plan, retrieve, and render.",
                bullets=["Planner", "Retrieval", "Rendering"],
                citations=["https://example.com/a?x=1&y=2"],
            )
        ],
        citations=["https://example.com/a?x=1&y=2"],
        related_links=[
            RelatedLink(
                label='Read more <here>',
                url="https://example.com/more",
                snippet="More details",
                follow_up_prompt="Tell me more about Read more <here>",
            )
        ],
        hero_image_url="https://example.com/hero.png",
        theme_hints={"theme_color": "#112233"},
        synthesis_mode="deterministic",
        synthesis_note="Rendered using deterministic fallback synthesis.",
        session_id="session-123",
        page_id="page-456",
    )

    html = renderer.render(page)

    assert "<!DOCTYPE html>" in html
    assert "Agentic &lt;Browser&gt;" in html
    assert 'A &quot;safe&quot; summary' in html
    assert 'src="https://example.com/hero.png"' in html
    assert "<h2>Overview</h2>" in html
    assert "<li>Planner</li>" in html
    assert "Read more &lt;here&gt;" in html
    assert "https://example.com/a?x=1&amp;y=2" in html
    assert "Fallback synthesis" in html
    assert "Rendered using deterministic fallback synthesis." in html
    assert "http://127.0.0.1:8000/agent/follow-up?session_id=session-123&amp;current_page_id=page-456" in html
    assert "http://127.0.0.1:8000/agent/pages/session-123/page-456" in html
    assert ":root {" in html
    assert ".page-shell {" in html
    assert "{{" not in html
    assert "}}" not in html


def test_renderer_applies_theme_color() -> None:
    renderer = DeterministicHtmlRenderer(base_url="http://127.0.0.1:8000")
    page = SynthesizedPage(
        title="Theme Test",
        hero_summary="Summary",
        sections=[],
        citations=[],
        theme_hints={"theme_color": "#2563eb"},
    )

    html = renderer.render(page)

    assert "--accent: #2563eb;" in html

from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage
from agentic_browser.rendering.html import DeterministicHtmlRenderer


def test_renderer_outputs_structured_html_and_escapes_content() -> None:
    renderer = DeterministicHtmlRenderer()
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
            )
        ],
        hero_image_url="https://example.com/hero.png",
        theme_hints={"theme_color": "#112233"},
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

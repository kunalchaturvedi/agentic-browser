from __future__ import annotations

from html import escape
from typing import Protocol

from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage


class RenderStrategy(Protocol):
    def render(self, page: SynthesizedPage) -> str:
        ...


class DeterministicHtmlRenderer:
    def render(self, page: SynthesizedPage) -> str:
        theme_color = escape(page.theme_hints.get("theme_color", "#2563eb"), quote=True)
        body = [
            "<!DOCTYPE html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\" />",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />",
            f"<title>{escape(page.title)}</title>",
            "<style>",
            ":root {{ color-scheme: light; }}",
            "body {{ font-family: Arial, sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }}",
            f".page {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 48px; border-top: 6px solid {theme_color}; }}",
            ".hero {{ background: white; border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(15,23,42,0.08); }}",
            ".hero img {{ width: 100%; max-height: 320px; object-fit: cover; border-radius: 12px; margin-top: 16px; }}",
            ".section {{ background: white; border-radius: 16px; padding: 20px 24px; margin-top: 20px; box-shadow: 0 8px 24px rgba(15,23,42,0.06); }}",
            ".section h2 {{ margin-top: 0; }}",
            ".citations, .related-links {{ padding-left: 20px; }}",
            ".related-links a, .citations a {{ color: #1d4ed8; text-decoration: none; }}",
            ".related-links a:hover, .citations a:hover {{ text-decoration: underline; }}",
            ".page-footer {{ margin-top: 28px; color: #475569; font-size: 0.95rem; }}",
            "</style>",
            "</head>",
            "<body>",
            "<main class=\"page\">",
            self._render_hero(page),
            *[self._render_section(section, index) for index, section in enumerate(page.sections, start=1)],
            self._render_related_links(page.related_links),
            self._render_page_citations(page.citations),
            "</main>",
            "</body>",
            "</html>",
        ]
        return "\n".join(part for part in body if part)

    def _render_hero(self, page: SynthesizedPage) -> str:
        image = (
            f'<img src="{escape(page.hero_image_url, quote=True)}" alt="{escape(page.title)} hero image" />'
            if page.hero_image_url
            else ""
        )
        return (
            "<section class=\"hero\">"
            f"<h1>{escape(page.title)}</h1>"
            f"<p>{escape(page.hero_summary)}</p>"
            f"{image}"
            "</section>"
        )

    def _render_section(self, section: PageSection, index: int) -> str:
        bullets = ""
        if section.bullets:
            bullet_items = "".join(f"<li>{escape(item)}</li>" for item in section.bullets)
            bullets = f"<ul>{bullet_items}</ul>"

        citations = ""
        if section.citations:
            citation_items = "".join(
                "<li>"
                f'<a href="{escape(url, quote=True)}">{escape(url)}</a>'
                "</li>"
                for url in section.citations
            )
            citations = f"<h3>Section citations</h3><ol class=\"citations\">{citation_items}</ol>"

        return (
            f'<section class="section" id="section-{index}">'
            f"<h2>{escape(section.title)}</h2>"
            f"<p>{escape(section.body)}</p>"
            f"{bullets}"
            f"{citations}"
            "</section>"
        )

    def _render_related_links(self, related_links: list[RelatedLink]) -> str:
        if not related_links:
            return ""

        items = "".join(
            "<li>"
            f'<a href="{escape(link.url, quote=True)}">{escape(link.label)}</a>'
            f"<p>{escape(link.snippet)}</p>"
            "</li>"
            for link in related_links
        )
        return (
            '<section class="section">'
            "<h2>Related links</h2>"
            f'<ul class="related-links">{items}</ul>'
            "</section>"
        )

    def _render_page_citations(self, citations: list[str]) -> str:
        if not citations:
            return '<footer class="page-footer">No citations were attached to this page.</footer>'

        items = "".join(
            "<li>"
            f'<a href="{escape(url, quote=True)}">{escape(url)}</a>'
            "</li>"
            for url in citations
        )
        return (
            '<footer class="page-footer">'
            "<h2>Sources</h2>"
            f'<ol class="citations">{items}</ol>'
            "</footer>"
        )


def get_renderer() -> RenderStrategy:
    return DeterministicHtmlRenderer()

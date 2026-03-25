from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Protocol
from urllib.parse import urlencode

from agentic_browser.config import get_settings
from agentic_browser.models.page import PageSection, RelatedLink, SynthesizedPage


class RenderStrategy(Protocol):
    def render(self, page: SynthesizedPage) -> str:
        ...


@dataclass
class DeterministicHtmlRenderer:
    base_url: str = "http://127.0.0.1:8000"

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
            ":root { color-scheme: light; --page-bg: #eef4ff; --page-bg-2: #f8fbff; --surface: rgba(255,255,255,0.88); --surface-strong: #ffffff; --surface-soft: rgba(255,255,255,0.72); --border: rgba(148,163,184,0.18); --text: #0f172a; --muted: #475569; --muted-soft: #64748b; --accent: {theme_color}; --accent-soft: color-mix(in srgb, {theme_color} 14%, white); --accent-strong: color-mix(in srgb, {theme_color} 78%, #0f172a); --shadow-xl: 0 30px 80px rgba(15,23,42,0.16); --shadow-lg: 0 20px 48px rgba(15,23,42,0.10); --shadow-md: 0 12px 28px rgba(15,23,42,0.08); --radius-2xl: 30px; --radius-xl: 24px; --radius-lg: 18px; --radius-md: 14px; --radius-sm: 10px; }".replace("{theme_color}", theme_color),
            "* { box-sizing: border-box; }",
            "html { background: linear-gradient(180deg, var(--page-bg) 0%, var(--page-bg-2) 42%, #ffffff 100%); }",
            "body { margin: 0; color: var(--text); font-family: Inter, Segoe UI, Arial, sans-serif; line-height: 1.65; background: radial-gradient(circle at top left, color-mix(in srgb, var(--accent) 14%, white) 0%, transparent 26%), radial-gradient(circle at top right, rgba(99,102,241,0.10) 0%, transparent 22%), linear-gradient(180deg, var(--page-bg) 0%, var(--page-bg-2) 42%, #ffffff 100%); }",
            "main, section, footer { display: block; }",
            ".page { max-width: 1180px; margin: 0 auto; padding: 30px 20px 72px; }",
            ".page-topbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 12px 2px 22px; }",
            ".brand { display: flex; align-items: center; gap: 12px; font-weight: 800; letter-spacing: -0.03em; color: var(--text); }",
            ".brand-mark { width: 40px; height: 40px; border-radius: 14px; background: linear-gradient(135deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 48%, #8b5cf6) 100%); box-shadow: 0 12px 26px color-mix(in srgb, var(--accent) 24%, transparent); position: relative; }",
            ".brand-mark::after { content: ''; position: absolute; inset: 10px; border-radius: 10px; background: rgba(255,255,255,0.88); }",
            ".brand-copy { display: flex; flex-direction: column; }",
            ".brand-title { font-size: 1rem; }",
            ".brand-subtitle { font-size: 0.82rem; color: var(--muted-soft); font-weight: 600; }",
            ".page-kicker { display: inline-flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px; background: rgba(255,255,255,0.72); border: 1px solid var(--border); box-shadow: var(--shadow-md); color: var(--muted); font-size: 0.88rem; font-weight: 700; }",
            ".page-shell { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 26px; align-items: start; }",
            ".main-column { min-width: 0; }",
            ".sidebar { display: grid; gap: 18px; position: sticky; top: 22px; }",
            ".hero, .section, .sidebar-card, .page-footer { backdrop-filter: blur(18px); background: linear-gradient(180deg, var(--surface-strong) 0%, var(--surface) 100%); border: 1px solid var(--border); box-shadow: var(--shadow-lg); }",
            ".hero { position: relative; overflow: hidden; border-radius: var(--radius-2xl); padding: 34px; display: grid; gap: 28px; }",
            ".hero::before { content: ''; position: absolute; inset: 0 auto auto 0; width: 180px; height: 180px; background: radial-gradient(circle, color-mix(in srgb, var(--accent) 18%, white) 0%, transparent 70%); pointer-events: none; }",
            ".hero.with-image { grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.85fr); align-items: center; }",
            ".hero-copy { min-width: 0; }",
            ".hero-kicker { display: inline-flex; align-items: center; gap: 10px; padding: 7px 12px; border-radius: 999px; background: var(--accent-soft); color: var(--accent-strong); font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }",
            ".hero-meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 18px 0 0; }",
            ".hero h1 { margin: 16px 0 0; font-size: clamp(2.35rem, 4vw, 4.15rem); line-height: 0.98; letter-spacing: -0.055em; max-width: 13ch; }",
            ".hero-summary { margin: 18px 0 0; font-size: 1.08rem; color: var(--muted); max-width: 62ch; }",
            ".hero-media { min-width: 0; }",
            ".hero img { width: 100%; aspect-ratio: 4 / 4.2; object-fit: cover; border-radius: 24px; display: block; box-shadow: var(--shadow-xl); border: 1px solid rgba(255,255,255,0.8); background: linear-gradient(135deg, rgba(15,23,42,0.08), rgba(255,255,255,0.7)); }",
            ".synthesis-badge { display: inline-flex; align-items: center; padding: 6px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; border: 1px solid transparent; }",
            ".synthesis-badge.llm { background: #dcfce7; color: #166534; border-color: rgba(22,101,52,0.18); }",
            ".synthesis-badge.deterministic { background: #fef3c7; color: #92400e; border-color: rgba(146,64,14,0.18); }",
            ".synthesis-note { margin: 0; color: var(--muted-soft); font-size: 0.92rem; }",
            ".section { border-radius: var(--radius-xl); padding: 26px 28px; margin-top: 22px; position: relative; overflow: hidden; }",
            ".section::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 4px; background: linear-gradient(180deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 30%, white) 100%); opacity: 0.95; }",
            ".section-index { display: inline-flex; align-items: center; justify-content: center; min-width: 34px; height: 34px; margin-bottom: 16px; border-radius: 999px; background: var(--accent-soft); color: var(--accent-strong); font-size: 0.82rem; font-weight: 800; letter-spacing: 0.04em; }",
            ".section-header { display: flex; align-items: start; justify-content: space-between; gap: 18px; }",
            ".section-title-block { min-width: 0; }",
            ".section h2 { margin: 0; font-size: 1.5rem; line-height: 1.12; letter-spacing: -0.03em; }",
            ".section p { margin: 0; color: var(--muted); }",
            ".section-body { margin-top: 14px; font-size: 1rem; }",
            ".section ul { list-style: none; margin: 20px 0 0; padding: 0; display: grid; gap: 12px; }",
            ".section li { position: relative; margin: 0; padding: 12px 14px 12px 46px; border-radius: var(--radius-md); background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.86) 100%); border: 1px solid rgba(148,163,184,0.16); box-shadow: 0 8px 18px rgba(15,23,42,0.04); }",
            ".section li::before { content: ''; position: absolute; left: 16px; top: 16px; width: 14px; height: 14px; border-radius: 999px; background: linear-gradient(135deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 45%, white) 100%); box-shadow: 0 0 0 5px color-mix(in srgb, var(--accent) 10%, white); }",
            ".section h3 { margin: 22px 0 10px; font-size: 0.78rem; letter-spacing: 0.11em; text-transform: uppercase; color: var(--muted-soft); }",
            ".section-citations { margin-top: 18px; padding-top: 18px; border-top: 1px solid rgba(148,163,184,0.14); }",
            ".citations { margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 10px; }",
            ".citations li { margin: 0; }",
            ".citations a { display: inline-flex; align-items: center; padding: 9px 12px; border-radius: 999px; background: rgba(255,255,255,0.8); border: 1px solid rgba(148,163,184,0.16); color: #1d4ed8; text-decoration: none; font-weight: 700; font-size: 0.9rem; }",
            ".citations a:hover { text-decoration: none; background: rgba(255,255,255,0.96); }",
            ".sidebar-card { border-radius: var(--radius-xl); padding: 20px; }",
            ".sidebar-card h2 { margin: 0 0 12px; font-size: 1.08rem; letter-spacing: -0.02em; }",
            ".sidebar-card p { margin: 0; color: var(--muted); font-size: 0.95rem; }",
            ".sidebar-stats { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 10px; margin-top: 14px; }",
            ".stat { padding: 14px 12px; border-radius: var(--radius-md); background: rgba(255,255,255,0.82); border: 1px solid rgba(148,163,184,0.14); }",
            ".stat-label { display: block; color: var(--muted-soft); font-size: 0.74rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }",
            ".stat-value { display: block; margin-top: 6px; font-size: 1.15rem; font-weight: 800; color: var(--text); }",
            ".related-links { list-style: none; padding: 0; margin: 16px 0 0; display: grid; gap: 14px; }",
            ".related-links li { padding: 18px; border-radius: var(--radius-lg); background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(248,250,252,0.9) 100%); border: 1px solid rgba(148,163,184,0.16); box-shadow: 0 12px 24px rgba(15,23,42,0.05); }",
            ".related-link-label { color: var(--text); text-decoration: none; font-size: 1rem; font-weight: 800; letter-spacing: -0.015em; }",
            ".related-link-label:hover { text-decoration: none; color: #1d4ed8; }",
            ".related-links p { margin: 10px 0 0; color: var(--muted); font-size: 0.95rem; }",
            ".link-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 14px; }",
            ".source-link { display: inline-flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 999px; background: rgba(15,23,42,0.04); color: var(--muted-soft); font-size: 0.9rem; font-weight: 700; text-decoration: none; }",
            ".source-link:hover { text-decoration: none; background: rgba(15,23,42,0.07); }",
            ".page-footer { margin-top: 32px; border-radius: var(--radius-xl); padding: 24px 26px; color: var(--muted); font-size: 0.96rem; }",
            ".footer-grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 24px; align-items: start; }",
            ".footer-grid h2 { margin: 0 0 12px; font-size: 1.15rem; color: var(--text); letter-spacing: -0.02em; }",
            ".footer-grid p { margin: 0; color: var(--muted); }",
            ".footer-links { margin-top: 16px; }",
            ".footer-links a { color: #1d4ed8; text-decoration: none; font-weight: 700; }",
            ".footer-links a:hover { text-decoration: underline; }",
            "@media (max-width: 980px) { .page-shell { grid-template-columns: 1fr; } .sidebar { position: static; order: 2; } .main-column { order: 1; } .hero.with-image { grid-template-columns: 1fr; } .hero img { aspect-ratio: 16 / 10; } .footer-grid { grid-template-columns: 1fr; } }",
            "@media (max-width: 760px) { .page { padding: 22px 14px 40px; } .page-topbar { flex-direction: column; align-items: flex-start; padding-bottom: 18px; } .hero, .section, .sidebar-card, .page-footer { padding: 20px; } .hero h1 { max-width: none; font-size: clamp(2rem, 11vw, 3rem); } .hero-summary { font-size: 1rem; } .section-header { display: block; } .citations { gap: 8px; } .citations a { font-size: 0.84rem; } }",
            "</style>",
            "</head>",
            "<body>",
            "<main class=\"page\">",
            self._render_page_topbar(page),
            '<div class="page-shell">',
            '<div class="main-column">',
            self._render_hero(page),
            *[self._render_section(section, index) for index, section in enumerate(page.sections, start=1)],
            self._render_page_citations(page, page.citations),
            "</div>",
            '<aside class="sidebar">',
            self._render_sidebar_summary(page),
            self._render_related_links(page, page.related_links),
            "</aside>",
            "</div>",
            "</main>",
            "</body>",
            "</html>",
        ]
        return "\n".join(part for part in body if part)

    def _render_page_topbar(self, page: SynthesizedPage) -> str:
        mode_label = "Live synthesis" if page.synthesis_mode == "llm" else "Rendered article"
        return (
            '<header class="page-topbar">'
            '<div class="brand">'
            '<span class="brand-mark" aria-hidden="true"></span>'
            '<span class="brand-copy">'
            '<span class="brand-title">Agentic Browser</span>'
            '<span class="brand-subtitle">Structured web reading experience</span>'
            "</span>"
            "</div>"
            f'<span class="page-kicker">{escape(mode_label)}</span>'
            "</header>"
        )

    def _render_hero(self, page: SynthesizedPage) -> str:
        synthesis_meta = self._render_synthesis_meta(page)
        hero_class = "hero with-image" if page.hero_image_url else "hero"
        image = (
            '<div class="hero-media">'
            f'<img src="{escape(page.hero_image_url, quote=True)}" alt="{escape(page.title)} hero image" />'
            "</div>"
            if page.hero_image_url
            else ""
        )
        return (
            f"<section class=\"{hero_class}\">"
            '<div class="hero-copy">'
            '<span class="hero-kicker">Generated page</span>'
            f"{synthesis_meta}"
            f"<h1>{escape(page.title)}</h1>"
            f'<p class="hero-summary">{escape(page.hero_summary)}</p>'
            "</div>"
            f"{image}"
            "</section>"
        )

    def _render_synthesis_meta(self, page: SynthesizedPage) -> str:
        if not page.synthesis_mode:
            return ""

        label = "LLM synthesis" if page.synthesis_mode == "llm" else "Fallback synthesis"
        note = f'<p class="synthesis-note">{escape(page.synthesis_note)}</p>' if page.synthesis_note else ""
        return (
            '<div class="hero-meta">'
            f'<span class="synthesis-badge {escape(page.synthesis_mode)}">{escape(label)}</span>'
            f"{note}"
            "</div>"
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
            citations = f'<div class="section-citations"><h3>Section citations</h3><ol class="citations">{citation_items}</ol></div>'

        return (
            f'<section class="section" id="section-{index}">'
            f'<span class="section-index">{index:02d}</span>'
            '<div class="section-header">'
            '<div class="section-title-block">'
            f"<h2>{escape(section.title)}</h2>"
            f'<p class="section-body">{escape(section.body)}</p>'
            "</div>"
            "</div>"
            f"{bullets}"
            f"{citations}"
            "</section>"
        )

    def _render_sidebar_summary(self, page: SynthesizedPage) -> str:
        return (
            '<section class="sidebar-card">'
            "<h2>Page summary</h2>"
            f"<p>{escape(page.context_summary or page.hero_summary)}</p>"
            '<div class="sidebar-stats">'
            f'<div class="stat"><span class="stat-label">Sections</span><span class="stat-value">{len(page.sections)}</span></div>'
            f'<div class="stat"><span class="stat-label">Sources</span><span class="stat-value">{len(page.citations)}</span></div>'
            "</div>"
            "</section>"
        )

    def _render_related_links(self, page: SynthesizedPage, related_links: list[RelatedLink]) -> str:
        if not related_links:
            return ""

        items = "".join(
            "<li>"
            f'<a class="related-link-label" href="{escape(self._build_follow_up_href(page, link), quote=True)}">{escape(link.label)}</a>'
            f"<p>{escape(link.snippet)}</p>"
            '<div class="link-actions">'
            f'<a class="source-link" href="{escape(link.url, quote=True)}">View original source</a>'
            "</div>"
            "</li>"
            for link in related_links
        )
        return (
            '<section class="sidebar-card">'
            "<h2>Related links</h2>"
            f'<ul class="related-links">{items}</ul>'
            "</section>"
        )

    def _render_page_citations(self, page: SynthesizedPage, citations: list[str]) -> str:
        if not citations:
            return (
                '<footer class="page-footer">'
                '<div class="footer-grid">'
                "<div><h2>Sources</h2><p>No citations were attached to this page.</p></div>"
                f'<div class="footer-links">{self._render_permalink(page)}</div>'
                "</div>"
                "</footer>"
            )

        items = "".join(
            "<li>"
            f'<a href="{escape(url, quote=True)}">{escape(url)}</a>'
            "</li>"
            for url in citations
        )
        return (
            '<footer class="page-footer">'
            '<div class="footer-grid">'
            "<div>"
            "<h2>Sources</h2>"
            "<p>Everything on this page is grounded in the URLs below.</p>"
            f'<ol class="citations">{items}</ol>'
            "</div>"
            f'<div class="footer-links">{self._render_permalink(page)}</div>'
            "</div>"
            "</footer>"
        )

    def _build_follow_up_href(self, page: SynthesizedPage, link: RelatedLink) -> str:
        if not page.session_id or not page.page_id:
            return link.url

        return self._absolute_internal_url("/agent/follow-up?" + urlencode(
            {
                "session_id": page.session_id,
                "current_page_id": page.page_id,
                "target_url": link.url,
                "target_label": link.label,
                "prompt": link.follow_up_prompt or f"Tell me more about {link.label}",
            }
        ))

    def _render_permalink(self, page: SynthesizedPage) -> str:
        if not page.session_id or not page.page_id:
            return ""

        permalink = self._absolute_internal_url(
            f"/agent/pages/{page.session_id}/{page.page_id}"
        )
        return (
            "<p>Keep or share this generated page.</p>"
            f'<p><a href="{permalink}">Permalink to this generated page</a></p>'
        )

    def _absolute_internal_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"


def get_renderer() -> RenderStrategy:
    settings = get_settings()
    return DeterministicHtmlRenderer(base_url=settings.app_base_url)

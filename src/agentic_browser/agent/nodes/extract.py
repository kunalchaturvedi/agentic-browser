from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from agentic_browser.agent.state import AgentGraphState
from agentic_browser.models.agent import ExtractedSource, FetchedSource


def _extract_style_hints(soup: BeautifulSoup) -> dict[str, str]:
    style_hints: dict[str, str] = {}

    theme_color = soup.find("meta", attrs={"name": "theme-color"})
    if theme_color and theme_color.get("content"):
        style_hints["theme_color"] = theme_color["content"]

    color_scheme = soup.find("meta", attrs={"name": "color-scheme"})
    if color_scheme and color_scheme.get("content"):
        style_hints["color_scheme"] = color_scheme["content"]

    body = soup.body
    if body and body.get("class"):
        style_hints["body_classes"] = " ".join(body.get("class", []))

    return style_hints


def _extract_image_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    image_urls: list[str] = []

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        image_urls.append(urljoin(base_url, og_image["content"]))

    for image in soup.find_all("img", src=True):
        image_urls.append(urljoin(base_url, image["src"]))
        if len(image_urls) >= 3:
            break

    deduped: list[str] = []
    for image_url in image_urls:
        if image_url not in deduped:
            deduped.append(image_url)

    return deduped[:3]


def _extract_single_source(source: FetchedSource) -> ExtractedSource:
    if not source.html:
        return ExtractedSource(
            title=source.title,
            url=source.url,
            snippet=source.snippet,
            content_preview=source.snippet,
            citations=[source.url],
        )

    soup = BeautifulSoup(source.html, "html.parser")
    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(["h1", "h2", "h3"])
        if heading.get_text(" ", strip=True)
    ][:5]

    paragraphs = [
        paragraph.get_text(" ", strip=True)
        for paragraph in soup.find_all("p")
        if paragraph.get_text(" ", strip=True)
    ]
    content_preview = " ".join(paragraphs[:3]) or source.snippet

    title_tag = soup.title.get_text(strip=True) if soup.title else source.title

    return ExtractedSource(
        title=title_tag,
        url=source.url,
        snippet=source.snippet,
        content_preview=content_preview[:800],
        headings=headings,
        citations=[source.url],
        image_urls=_extract_image_urls(soup, source.url),
        style_hints=_extract_style_hints(soup),
    )


def extract_sources_node(state: AgentGraphState) -> AgentGraphState:
    fetched_sources = state.get("fetched_sources", [])
    extracted_sources = [_extract_single_source(source) for source in fetched_sources]
    return {"extracted_sources": extracted_sources}


def finalize_agent_response(state: AgentGraphState) -> AgentGraphState:
    request = state["request"]
    planner = state["planner"]
    search_results = state.get("search_results", [])
    selected_sources = state.get("selected_sources", [])
    extracted_sources = state.get("extracted_sources", [])
    page = state["page"]

    if planner.decision.value == "answer_from_context":
        summary = (
            "Planner chose to answer from the current context without web retrieval "
            f"and synthesized {len(page.sections)} page sections."
        )
    else:
        summary = (
            "Planner chose web retrieval and gathered "
            f"{len(search_results)} results, selected {len(selected_sources)} sources, "
            f"extracted {len(extracted_sources)} evidence packets, and synthesized "
            f"{len(page.sections)} page sections."
        )

    return {
        "response": {
            "prompt": request.prompt,
            "planner": planner,
            "search_results": search_results,
            "selected_sources": selected_sources,
            "extracted_sources": extracted_sources,
            "page": page,
            "summary": summary,
        }
    }

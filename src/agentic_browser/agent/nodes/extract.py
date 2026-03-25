from __future__ import annotations

import json
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


def _normalize_recipe_instruction(item: object) -> list[str]:
    if isinstance(item, str):
        text = item.strip()
        return [text] if text else []
    if isinstance(item, dict):
        if isinstance(item.get("text"), str) and item["text"].strip():
            return [item["text"].strip()]
        if isinstance(item.get("itemListElement"), list):
            steps: list[str] = []
            for child in item["itemListElement"]:
                steps.extend(_normalize_recipe_instruction(child))
            return steps
    if isinstance(item, list):
        steps: list[str] = []
        for child in item:
            steps.extend(_normalize_recipe_instruction(child))
        return steps
    return []


def _find_recipe_schema_objects(raw: object) -> list[dict]:
    candidates: list[dict] = []
    if isinstance(raw, dict):
        if raw.get("@type") == "Recipe" or (
            isinstance(raw.get("@type"), list) and "Recipe" in raw.get("@type", [])
        ):
            candidates.append(raw)
        if isinstance(raw.get("@graph"), list):
            for item in raw["@graph"]:
                candidates.extend(_find_recipe_schema_objects(item))
    elif isinstance(raw, list):
        for item in raw:
            candidates.extend(_find_recipe_schema_objects(item))
    return candidates


def _extract_recipe_fields(soup: BeautifulSoup) -> tuple[list[str], list[str], list[str]]:
    ingredients: list[str] = []
    steps: list[str] = []
    notes: list[str] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            parsed = json.loads(script.string)
        except (TypeError, ValueError):
            continue

        for recipe in _find_recipe_schema_objects(parsed):
            for ingredient in recipe.get("recipeIngredient", []):
                if isinstance(ingredient, str) and ingredient.strip():
                    ingredients.append(ingredient.strip())

            steps.extend(_normalize_recipe_instruction(recipe.get("recipeInstructions", [])))

            description = recipe.get("description")
            if isinstance(description, str) and description.strip():
                notes.append(description.strip())

            recipe_yield = recipe.get("recipeYield")
            if isinstance(recipe_yield, str) and recipe_yield.strip():
                notes.append(f"Yield: {recipe_yield.strip()}")

            total_time = recipe.get("totalTime")
            if isinstance(total_time, str) and total_time.strip():
                notes.append(f"Total time: {total_time.strip()}")

    return ingredients[:15], steps[:12], notes[:6]


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
    list_items = [
        item.get_text(" ", strip=True)
        for item in soup.find_all("li")
        if item.get_text(" ", strip=True)
    ][:12]
    content_preview_parts = paragraphs[:5]
    if len(content_preview_parts) < 5:
        content_preview_parts.extend(list_items[: max(0, 5 - len(content_preview_parts))])
    content_preview = " ".join(content_preview_parts) or source.snippet

    title_tag = soup.title.get_text(strip=True) if soup.title else source.title
    recipe_ingredients, recipe_steps, recipe_notes = _extract_recipe_fields(soup)

    return ExtractedSource(
        title=title_tag,
        url=source.url,
        snippet=source.snippet,
        content_preview=content_preview[:800],
        headings=headings,
        list_items=list_items,
        citations=[source.url],
        image_urls=_extract_image_urls(soup, source.url),
        style_hints=_extract_style_hints(soup),
        recipe_ingredients=recipe_ingredients,
        recipe_steps=recipe_steps,
        recipe_notes=recipe_notes,
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

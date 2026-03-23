from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PageSection(BaseModel):
    title: str
    body: str
    bullets: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class RelatedLink(BaseModel):
    label: str
    url: str
    snippet: str = ""


class SynthesizedPage(BaseModel):
    title: str
    hero_summary: str
    sections: list[PageSection] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    related_links: list[RelatedLink] = Field(default_factory=list)
    hero_image_url: Optional[str] = None
    theme_hints: dict[str, str] = Field(default_factory=dict)

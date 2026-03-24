from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from uuid import uuid4

from agentic_browser.models.page import SynthesizedPage


@dataclass(frozen=True)
class StoredPage:
    session_id: str
    page_id: str
    prompt: str
    page: SynthesizedPage
    context_summary: str


class InMemoryNavigationStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, StoredPage]] = {}
        self._lock = RLock()

    @staticmethod
    def create_session_id() -> str:
        return uuid4().hex

    @staticmethod
    def create_page_id() -> str:
        return uuid4().hex

    def save_page(self, session_id: str, prompt: str, page: SynthesizedPage) -> StoredPage:
        if not page.page_id:
            raise ValueError("page.page_id must be set before saving navigation state.")

        stored_page = StoredPage(
            session_id=session_id,
            page_id=page.page_id,
            prompt=prompt,
            page=page,
            context_summary=page.context_summary or page.hero_summary,
        )
        with self._lock:
            self._sessions.setdefault(session_id, {})[page.page_id] = stored_page
        return stored_page

    def get_page(self, session_id: str, page_id: str) -> StoredPage | None:
        with self._lock:
            return self._sessions.get(session_id, {}).get(page_id)


_navigation_store = InMemoryNavigationStore()


def get_navigation_store() -> InMemoryNavigationStore:
    return _navigation_store

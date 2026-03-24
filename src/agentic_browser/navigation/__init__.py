"""Navigation support for local browsing continuity."""

from agentic_browser.navigation.store import (
    InMemoryNavigationStore,
    StoredPage,
    get_navigation_store,
)

__all__ = [
    "InMemoryNavigationStore",
    "StoredPage",
    "get_navigation_store",
]

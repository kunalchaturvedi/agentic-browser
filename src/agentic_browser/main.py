import logging

from fastapi import FastAPI

from agentic_browser.config import get_settings
from agentic_browser.routes.agent import router as agent_router
from agentic_browser.routes.health import router as health_router
from agentic_browser.routes.search import router as search_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)
app.include_router(agent_router)
app.include_router(health_router)
app.include_router(search_router)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "status": "running",
    }

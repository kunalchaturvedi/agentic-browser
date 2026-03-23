from agentic_browser.config import get_settings

import uvicorn


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "agentic_browser.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )

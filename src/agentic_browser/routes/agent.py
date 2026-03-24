import logging

import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from agentic_browser.agent.graph import AgentWorkflow, get_agent_workflow
from agentic_browser.models.agent import AgentRequest, AgentResponse
from agentic_browser.rendering import RenderStrategy, get_renderer
from agentic_browser.services.search import SearchConfigurationError

router = APIRouter(tags=["agent"])
logger = logging.getLogger("uvicorn.error")


@router.post("/agent", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    workflow: AgentWorkflow = Depends(get_agent_workflow),
) -> AgentResponse:
    logger.info(
        "Received /agent request prompt=%r max_results=%s max_sources=%s has_context=%s",
        request.prompt,
        request.max_results,
        request.max_sources,
        bool(request.context_summary),
    )
    try:
        response = await workflow.run(request)
        logger.info(
            "Completed /agent request prompt=%r decision=%s search_results=%s extracted_sources=%s page_sections=%s",
            request.prompt,
            response.planner.decision.value,
            len(response.search_results),
            len(response.extracted_sources),
            len(response.page.sections),
        )
        return response
    except SearchConfigurationError as exc:
        logger.warning("Agent search configuration error for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Agent retrieval HTTP error for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent retrieval provider returned an error.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Agent retrieval request failure for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent retrieval request failed.",
        ) from exc


@router.post("/agent/render", response_class=HTMLResponse)
async def render_agent_page(
    request: AgentRequest,
    workflow: AgentWorkflow = Depends(get_agent_workflow),
    renderer: RenderStrategy = Depends(get_renderer),
) -> HTMLResponse:
    logger.info(
        "Received /agent/render request prompt=%r max_results=%s max_sources=%s has_context=%s",
        request.prompt,
        request.max_results,
        request.max_sources,
        bool(request.context_summary),
    )
    try:
        response = await workflow.run(request)
        html = renderer.render(response.page)
        logger.info(
            "Completed /agent/render request prompt=%r decision=%s page_sections=%s",
            request.prompt,
            response.planner.decision.value,
            len(response.page.sections),
        )
        return HTMLResponse(content=html)
    except SearchConfigurationError as exc:
        logger.warning("Render search configuration error for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Render retrieval HTTP error for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Render retrieval provider returned an error.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Render retrieval request failure for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Render retrieval request failed.",
        ) from exc

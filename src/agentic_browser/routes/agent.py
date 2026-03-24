import logging
from typing import Optional

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from agentic_browser.agent.graph import AgentWorkflow, get_agent_workflow
from agentic_browser.models.agent import AgentRequest, AgentResponse
from agentic_browser.navigation import InMemoryNavigationStore, StoredPage, get_navigation_store
from agentic_browser.rendering import RenderStrategy, get_renderer
from agentic_browser.services.search import SearchConfigurationError

router = APIRouter(tags=["agent"])
logger = logging.getLogger("uvicorn.error")


def _get_stored_page(
    navigation_store: InMemoryNavigationStore,
    session_id: str,
    page_id: str,
) -> StoredPage:
    stored_page = navigation_store.get_page(session_id, page_id)
    if stored_page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Navigation context was not found for the requested page.",
        )
    return stored_page


def _prepare_request(
    request: AgentRequest,
    navigation_store: InMemoryNavigationStore,
) -> AgentRequest:
    if request.context_summary or not (request.session_id and request.current_page_id):
        return request

    stored_page = _get_stored_page(
        navigation_store=navigation_store,
        session_id=request.session_id,
        page_id=request.current_page_id,
    )
    return request.model_copy(
        update={
            "context_summary": stored_page.context_summary,
        }
    )


def _store_response_page(
    request: AgentRequest,
    response: AgentResponse,
    navigation_store: InMemoryNavigationStore,
) -> AgentResponse:
    session_id = request.session_id or navigation_store.create_session_id()
    page_id = navigation_store.create_page_id()
    page = response.page.model_copy(
        update={
            "session_id": session_id,
            "page_id": page_id,
            "context_summary": response.page.context_summary or response.page.hero_summary,
        }
    )
    navigation_store.save_page(
        session_id=session_id,
        prompt=request.prompt,
        page=page,
    )
    return response.model_copy(
        update={
            "session_id": session_id,
            "page_id": page_id,
            "page": page,
        }
    )


@router.post("/agent", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    workflow: AgentWorkflow = Depends(get_agent_workflow),
    navigation_store: InMemoryNavigationStore = Depends(get_navigation_store),
) -> AgentResponse:
    prepared_request = _prepare_request(request, navigation_store)
    logger.info(
        "Received /agent request prompt=%r max_results=%s max_sources=%s has_context=%s session_id=%s current_page_id=%s",
        prepared_request.prompt,
        prepared_request.max_results,
        prepared_request.max_sources,
        bool(prepared_request.context_summary),
        prepared_request.session_id,
        prepared_request.current_page_id,
    )
    try:
        response = await workflow.run(prepared_request)
        response = _store_response_page(prepared_request, response, navigation_store)
        logger.info(
            "Completed /agent request prompt=%r decision=%s search_results=%s extracted_sources=%s page_sections=%s session_id=%s page_id=%s",
            prepared_request.prompt,
            response.planner.decision.value,
            len(response.search_results),
            len(response.extracted_sources),
            len(response.page.sections),
            response.session_id,
            response.page_id,
        )
        return response
    except SearchConfigurationError as exc:
        logger.warning("Agent search configuration error for prompt=%r: %s", prepared_request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Agent retrieval HTTP error for prompt=%r: %s", prepared_request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent retrieval provider returned an error.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Agent retrieval request failure for prompt=%r: %s", prepared_request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent retrieval request failed.",
        ) from exc


@router.post("/agent/render", response_class=HTMLResponse)
async def render_agent_page(
    request: AgentRequest,
    workflow: AgentWorkflow = Depends(get_agent_workflow),
    renderer: RenderStrategy = Depends(get_renderer),
    navigation_store: InMemoryNavigationStore = Depends(get_navigation_store),
) -> HTMLResponse:
    prepared_request = _prepare_request(request, navigation_store)
    logger.info(
        "Received /agent/render request prompt=%r max_results=%s max_sources=%s has_context=%s session_id=%s current_page_id=%s",
        prepared_request.prompt,
        prepared_request.max_results,
        prepared_request.max_sources,
        bool(prepared_request.context_summary),
        prepared_request.session_id,
        prepared_request.current_page_id,
    )
    try:
        response = await workflow.run(prepared_request)
        response = _store_response_page(prepared_request, response, navigation_store)
        html = renderer.render(response.page)
        logger.info(
            "Completed /agent/render request prompt=%r decision=%s page_sections=%s session_id=%s page_id=%s",
            prepared_request.prompt,
            response.planner.decision.value,
            len(response.page.sections),
            response.session_id,
            response.page_id,
        )
        return HTMLResponse(content=html)
    except SearchConfigurationError as exc:
        logger.warning("Render search configuration error for prompt=%r: %s", prepared_request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Render retrieval HTTP error for prompt=%r: %s", prepared_request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Render retrieval provider returned an error.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Render retrieval request failure for prompt=%r: %s", prepared_request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Render retrieval request failed.",
        ) from exc


@router.get("/agent/pages/{session_id}/{page_id}", response_class=HTMLResponse)
async def render_stored_page(
    session_id: str,
    page_id: str,
    renderer: RenderStrategy = Depends(get_renderer),
    navigation_store: InMemoryNavigationStore = Depends(get_navigation_store),
) -> HTMLResponse:
    stored_page = _get_stored_page(navigation_store, session_id, page_id)
    logger.info("Rendering stored page session_id=%s page_id=%s", session_id, page_id)
    return HTMLResponse(content=renderer.render(stored_page.page))


@router.get("/agent/follow-up", response_class=HTMLResponse)
async def follow_up_agent_page(
    session_id: str,
    current_page_id: str,
    target_url: str,
    target_label: str,
    prompt: Optional[str] = Query(default=None),
    max_results: int = Query(default=5, ge=1, le=10),
    max_sources: int = Query(default=3, ge=1, le=5),
    workflow: AgentWorkflow = Depends(get_agent_workflow),
    renderer: RenderStrategy = Depends(get_renderer),
    navigation_store: InMemoryNavigationStore = Depends(get_navigation_store),
) -> HTMLResponse:
    stored_page = _get_stored_page(navigation_store, session_id, current_page_id)
    follow_up_prompt = prompt or f"Tell me more about {target_label}"
    request = AgentRequest(
        prompt=f"{follow_up_prompt} ({target_url})",
        context_summary=stored_page.context_summary,
        max_results=max_results,
        max_sources=max_sources,
        session_id=session_id,
        current_page_id=current_page_id,
        navigation_target_url=target_url,
    )
    logger.info(
        "Received /agent/follow-up request prompt=%r session_id=%s current_page_id=%s target_url=%s",
        request.prompt,
        session_id,
        current_page_id,
        target_url,
    )
    try:
        response = await workflow.run(request)
        response = _store_response_page(request, response, navigation_store)
        html = renderer.render(response.page)
        logger.info(
            "Completed /agent/follow-up request prompt=%r decision=%s session_id=%s page_id=%s",
            request.prompt,
            response.planner.decision.value,
            response.session_id,
            response.page_id,
        )
        return HTMLResponse(content=html)
    except SearchConfigurationError as exc:
        logger.warning("Follow-up search configuration error for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Follow-up retrieval HTTP error for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Follow-up retrieval provider returned an error.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Follow-up retrieval request failure for prompt=%r: %s", request.prompt, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Follow-up retrieval request failed.",
        ) from exc

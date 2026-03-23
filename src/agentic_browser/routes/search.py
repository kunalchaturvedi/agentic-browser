import logging

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status

from agentic_browser.models.search import SearchQuery, SearchResponse
from agentic_browser.services.search import (
    SearchConfigurationError,
    SearchService,
    get_search_service,
)

router = APIRouter(tags=["search"])
logger = logging.getLogger("uvicorn.error")


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of results"),
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    query = SearchQuery(q=q, limit=limit)
    logger.info("Received /search request query=%r limit=%s", query.q, query.limit)

    try:
        response = await service.search(query=query.q, limit=query.limit)
        logger.info(
            "Completed /search request query=%r results=%s",
            query.q,
            response.total_results,
        )
        return response
    except SearchConfigurationError as exc:
        logger.warning("Search configuration error for query=%r: %s", query.q, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Search provider HTTP error for query=%r: %s", query.q, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Search provider returned an error.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Search provider request failure for query=%r: %s", query.q, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Search provider request failed.",
        ) from exc

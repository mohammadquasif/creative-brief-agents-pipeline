"""Public REST endpoints for the pipeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..core.config import Settings, get_settings
from ..core.exceptions import InvalidBriefError, ProviderError
from ..schemas.generation import GenerationRequest, GenerationResponse
from ..services.pipeline import Pipeline, create_pipeline

router = APIRouter(prefix="/api/v1", tags=["pipeline"])


def get_pipeline(settings: Settings = Depends(get_settings)) -> Pipeline:
    """Dependency: cached, fully-wired pipeline for this request."""
    return create_pipeline(settings)


@router.post(
    "/generate",
    response_model=GenerationResponse,
    summary="Turn a messy creative brief into validated creative output.",
    responses={
        422: {
            "description": "Brief could not be validated after retries + fallbacks.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "brief_validation_failed",
                        "message": "Brief could not be validated after 3 attempt(s).",
                        "issues": [{"field": "deadline", "message": "..."}],
                        "attempts": 3,
                    }
                }
            },
        },
        503: {"description": "The configured LLM provider is unavailable."},
    },
)
def generate(
    request: GenerationRequest,
    pipeline: Pipeline = Depends(get_pipeline),
) -> GenerationResponse:
    """POST /generate — send raw brief text, get back creative output."""
    try:
        return pipeline.run(request)
    except InvalidBriefError as exc:
        # Explicit, structured error: we refuse to pass bad data downstream.
        raise HTTPException(
            status_code=422,
            detail={
                "error": "brief_validation_failed",
                "message": exc.summary,
                "issues": [issue.model_dump() for issue in exc.issues],
                "attempts": exc.attempts,
                "fallbacks_applied": exc.fallbacks_applied,
            },
        ) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "provider_unavailable", "message": str(exc)},
        ) from exc


@router.get("/health", summary="Liveness check.")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {"status": "ok", "provider": settings.llm_provider}


@router.get("/provider", summary="Which 'brain' is powering the agents.")
def provider_info(pipeline: Pipeline = Depends(get_pipeline)) -> dict:
    return {"provider": pipeline.provider_name}

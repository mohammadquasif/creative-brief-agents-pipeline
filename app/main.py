"""FastAPI application entrypoint.

Run locally:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .api.routes import router
from .core.config import get_settings
from .core.logging import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Two-agent pipeline: Agent 1 (Parser) turns a messy creative brief "
            "into structured fields; a validation gate (retry -> fallback -> "
            "clear error) guards the handoff; Agent 2 (Generator) produces "
            "creative output from the validated brief."
        ),
    )
    app.include_router(router)

    @app.get("/", tags=["meta"], include_in_schema=False)
    def root() -> dict:
        return {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": "/api/v1/health",
            "generate": "POST /api/v1/generate",
        }

    return app


app = create_app()

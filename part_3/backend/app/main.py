"""FastAPI app assembly for the MYH applications data service."""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.exception_handlers import register_exception_handlers
from backend.app.logging_config import configure_logging
from backend.app.routers import applications, export, health, operations, providers, stats


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="MYH Applications API",
        version="0.3.11",
        description="Read and operational API for the curated MYH applications dataset stored in PostgreSQL.",
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(applications.router)
    app.include_router(stats.router)
    app.include_router(providers.router)
    app.include_router(export.router)
    app.include_router(operations.router)
    return app


app = create_app()

"""FastAPI app assembly for the MYH applications data service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.exception_handlers import register_exception_handlers
from backend.app.logging_config import configure_logging
from backend.app.routers import admin, applications, export, health, operations, providers, stats
from backend.app.services.database_seeder import ensure_database_ready


def build_lifespan(run_startup_seeder: bool = True):
    """Build the FastAPI lifespan handler.

    Tests can disable the startup seeder explicitly, while the real app keeps
    database bootstrap enabled by default.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if run_startup_seeder:
            ensure_database_ready()
        yield

    return lifespan


def create_app(*, run_startup_seeder: bool = True) -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="MYH Applications API",
        version="0.3.12.1",
        description="Read, operational, and protected-admin API for the curated MYH applications dataset stored in PostgreSQL.",
        lifespan=build_lifespan(run_startup_seeder),
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(applications.router)
    app.include_router(stats.router)
    app.include_router(providers.router)
    app.include_router(export.router)
    app.include_router(operations.router)
    app.include_router(admin.router)
    return app


app = create_app()

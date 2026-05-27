"""FastAPI app assembly for the MYH applications data service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.exception_handlers import register_exception_handlers
from backend.app.logging_config import configure_logging
from backend.app.routers import admin, applications, export, health, operations, providers, stats
from backend.app.services.database_seeder import ensure_database_ready


LOCAL_DASHBOARD_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def add_local_dashboard_cors(app: FastAPI) -> None:
    """Allow the local Vite dashboard to call the public backend API.

    This is a local-development convenience for the React dashboard. It does
    not expose admin tokens and does not change protected admin behavior.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_DASHBOARD_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )


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
        version="0.3.13",
        description="Read, operational, and protected-admin API for the curated MYH applications dataset stored in PostgreSQL.",
        lifespan=build_lifespan(run_startup_seeder),
    )
    register_exception_handlers(app)
    add_local_dashboard_cors(app)

    app.include_router(health.router)
    app.include_router(applications.router)
    app.include_router(stats.router)
    app.include_router(providers.router)
    app.include_router(export.router)
    app.include_router(operations.router)
    app.include_router(admin.router)
    return app


app = create_app()

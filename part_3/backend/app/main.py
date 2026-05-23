"""FastAPI entry point for the MYH applications data service."""

from __future__ import annotations

from fastapi import FastAPI


app = FastAPI(
    title="MYH Applications API",
    version="0.3.3",
    description="Read API for the curated MYH applications dataset stored in PostgreSQL.",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a small service description for manual browser checks."""
    return {
        "service": "MYH Applications API",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def read_health() -> dict[str, str]:
    """Return a simple health check response."""
    return {"status": "ok"}

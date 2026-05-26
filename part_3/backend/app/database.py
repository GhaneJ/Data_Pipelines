"""Database connection helpers for the FastAPI backend."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row


class DatabaseConfigurationError(RuntimeError):
    """Raised when required database configuration is missing or invalid."""


def get_database_url(database_url: str | None = None) -> str:
    """Return an explicit or environment PostgreSQL connection URL."""
    resolved_url = database_url or os.getenv("DATABASE_URL")
    if not resolved_url:
        raise DatabaseConfigurationError("DATABASE_URL is not set. Configure it before starting the API.")
    return resolved_url


@contextmanager
def open_connection(database_url: str | None = None) -> Iterator[psycopg.Connection[dict[str, Any]]]:
    """Open a PostgreSQL connection using DATABASE_URL or an explicit URL."""
    with psycopg.connect(get_database_url(database_url), row_factory=dict_row) as conn:
        yield conn

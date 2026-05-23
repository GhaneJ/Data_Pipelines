"""Database connection helpers for the FastAPI read API."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row


@contextmanager
def open_connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    """Open a PostgreSQL connection using the DATABASE_URL environment variable."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Configure it before starting the API.")

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        yield conn

"""Simple protected-admin helpers for write-side backend operations."""

from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status


ADMIN_TOKEN_ENV_VAR = "PART3_ADMIN_TOKEN"
ADMIN_TOKEN_HEADER = "X-Admin-Token"


class AdminAuthConfigurationError(RuntimeError):
    """Raised when protected-admin auth is not configured on the server."""


def get_configured_admin_token() -> str:
    """Return the configured local admin token or fail clearly."""
    token = os.getenv(ADMIN_TOKEN_ENV_VAR, "").strip()
    if not token:
        raise AdminAuthConfigurationError(
            f"{ADMIN_TOKEN_ENV_VAR} is not configured. Set it before using protected admin endpoints."
        )
    return token


def verify_admin_token(provided_token: str | None, expected_token: str | None = None) -> str:
    """Validate one admin token value and return it when accepted."""
    token_to_compare = expected_token if expected_token is not None else get_configured_admin_token()
    if not token_to_compare.strip():
        raise AdminAuthConfigurationError(
            f"{ADMIN_TOKEN_ENV_VAR} is not configured. Set it before using protected admin endpoints."
        )

    if provided_token is None or not provided_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {ADMIN_TOKEN_HEADER} header for protected admin operation.",
        )

    if not secrets.compare_digest(provided_token.strip(), token_to_compare.strip()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token for protected admin operation.",
        )

    return provided_token.strip()


def require_admin_token(
    x_admin_token: Annotated[str | None, Header(alias=ADMIN_TOKEN_HEADER)] = None,
) -> str:
    """FastAPI dependency requiring the configured local admin token."""
    try:
        return verify_admin_token(x_admin_token)
    except AdminAuthConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

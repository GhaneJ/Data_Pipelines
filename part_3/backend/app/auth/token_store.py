"""Retired 3.15 environment request-token module.

Database-backed authentication in 3.15.1 no longer authenticates requests from
static request-time credentials. This module remains only to make the removal
explicit for older imports during transition; new code must use
backend.app.auth.dependencies, routes, repositories, password_hashing, and tokens.
"""

from __future__ import annotations


class RetiredEnvironmentTokenAuthentication(RuntimeError):
    """Raised if removed environment-token authentication is used."""


def authenticate_token(token: str | None):  # pragma: no cover - defensive compatibility only
    """Fail clearly because static request-time tokens are no longer supported."""
    raise RetiredEnvironmentTokenAuthentication("Static request-time tokens were retired in 3.15.1.")

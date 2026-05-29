"""Database-backed authentication and authorization helpers for the backend API."""

from backend.app.auth.models import AuthenticatedPrincipal, Role

__all__ = ["AuthenticatedPrincipal", "Role"]

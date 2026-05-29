"""Authentication inspection routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.auth.dependencies import CurrentPrincipal
from backend.app.auth.models import AuthenticatedPrincipal


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/whoami", response_model=AuthenticatedPrincipal)
def whoami(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
    """Return the safe authenticated principal for a valid bearer token."""
    return principal

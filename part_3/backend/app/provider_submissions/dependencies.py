"""Provider-specific dependencies for application submission routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from backend.app.auth.dependencies import ProviderPrincipal
from backend.app.dependencies import DatabaseConnection
from backend.app.provider_submissions.models import ProviderSubmissionIdentity
from backend.app.provider_submissions.repositories import get_provider_name


_PROVIDER_ID_MISSING = "Authenticated provider user is missing a provider id."
_INVALID_PROVIDER_SUBJECT = "Authenticated provider user has an invalid subject."


def _user_id_from_subject(subject: str) -> UUID:
    """Extract the database user id from an AuthenticatedPrincipal subject."""
    prefix = "user:"
    if not subject.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_PROVIDER_SUBJECT)
    try:
        return UUID(subject.removeprefix(prefix))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_PROVIDER_SUBJECT) from exc


def get_provider_submission_identity(
    conn: DatabaseConnection,
    principal: ProviderPrincipal,
) -> ProviderSubmissionIdentity:
    """Resolve the authenticated provider identity for submission ownership."""
    if principal.provider_id is None or not principal.provider_id.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_PROVIDER_ID_MISSING)

    provider_id = principal.provider_id.strip()
    provider_name = get_provider_name(conn, provider_id) or principal.display_name
    return ProviderSubmissionIdentity(
        user_id=_user_id_from_subject(principal.subject),
        provider_id=provider_id,
        provider_name=provider_name,
    )


ProviderSubmissionPrincipal = Annotated[ProviderSubmissionIdentity, Depends(get_provider_submission_identity)]

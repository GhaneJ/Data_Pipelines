"""Admin-only API key management routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from backend.app.api_keys.key_utils import extract_key_prefix, generate_api_key, hash_api_key
from backend.app.api_keys.models import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyListItem, APIKeyRevokeResponse
from backend.app.api_keys.repositories import create_api_key_record, list_api_key_records, revoke_api_key_record
from backend.app.auth.dependencies import AdminRoutePrincipal
from backend.app.auth.tokens import utc_now
from backend.app.dependencies import DatabaseConnection

router = APIRouter(prefix="/admin/api-keys", tags=["admin", "api-keys"])
AdminPrincipal = AdminRoutePrincipal


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: APIKeyCreateRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> APIKeyCreateResponse:
    """Create a database-backed API key and return the raw key once."""
    raw_api_key = generate_api_key()
    expires_at = utc_now() + timedelta(days=payload.expires_in_days) if payload.expires_in_days is not None else None
    row = create_api_key_record(
        conn,
        name=payload.name,
        description=payload.description,
        key_prefix=extract_key_prefix(raw_api_key),
        key_hash=hash_api_key(raw_api_key),
        scopes=payload.scopes,
        expires_at=expires_at,
        created_by_user_id=admin_principal.subject.removeprefix("user:"),
    )
    return APIKeyCreateResponse(api_key=raw_api_key, **row)


@router.get("", response_model=list[APIKeyListItem])
def list_api_keys(conn: DatabaseConnection, admin_principal: AdminPrincipal) -> list[dict[str, object]]:
    """List safe API key metadata for admins."""
    return list_api_key_records(conn)


@router.post("/{key_id}/revoke", response_model=APIKeyRevokeResponse)
def revoke_api_key(
    key_id: str,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> APIKeyRevokeResponse:
    """Revoke one API key idempotently."""
    row = revoke_api_key_record(
        conn,
        key_id=key_id,
        revoked_by_user_id=admin_principal.subject.removeprefix("user:"),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"API key {key_id!r} was not found.")
    return APIKeyRevokeResponse(id=str(row["id"]), revoked=True)

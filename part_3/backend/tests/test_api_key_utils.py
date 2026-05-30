"""Unit tests for API key generation, hashing, and safe prefixes."""

from __future__ import annotations

from backend.app.api_keys.key_utils import API_KEY_PREFIX, extract_key_prefix, generate_api_key, hash_api_key, verify_api_key_hash
from backend.app.api_keys.models import APIKeyListItem
from backend.app.auth.tokens import utc_now


def test_generated_api_keys_are_random_and_prefixed() -> None:
    first = generate_api_key()
    second = generate_api_key()

    assert first != second
    assert first.startswith(API_KEY_PREFIX)
    assert second.startswith(API_KEY_PREFIX)
    assert len(first) > 40


def test_api_key_hashing_never_returns_raw_key() -> None:
    raw = generate_api_key()
    stored_hash = hash_api_key(raw)

    assert stored_hash != raw
    assert hash_api_key(raw) == stored_hash
    assert hash_api_key(raw + "x") != stored_hash
    assert verify_api_key_hash(raw, stored_hash) is True
    assert verify_api_key_hash(raw + "x", stored_hash) is False


def test_key_prefix_is_non_secret_display_identifier() -> None:
    raw = generate_api_key()
    prefix = extract_key_prefix(raw)

    assert raw.startswith(prefix)
    assert prefix.startswith(API_KEY_PREFIX)
    assert prefix != raw
    assert len(prefix) < len(raw)


def test_list_model_does_not_contain_raw_api_key_or_hash() -> None:
    item = APIKeyListItem(
        id="00000000-0000-0000-0000-000000000001",
        name="Local export client",
        description="Local CSV export testing",
        key_prefix="part3_example",
        scopes=["export:read"],
        is_active=True,
        expires_at=None,
        revoked_at=None,
        created_at=utc_now(),
        last_used_at=None,
    )

    dumped = item.model_dump()
    assert "api_key" not in dumped
    assert "key_hash" not in dumped

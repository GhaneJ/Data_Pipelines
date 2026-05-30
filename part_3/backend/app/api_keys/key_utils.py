"""Utility helpers for opaque database-backed API keys."""

from __future__ import annotations

import hashlib
import hmac
import secrets

API_KEY_PREFIX = "part3_"
API_KEY_RANDOM_BYTES = 32
API_KEY_HASH_ALGORITHM = "sha256"
DISPLAY_PREFIX_BODY_CHARS = 10


def generate_api_key() -> str:
    """Generate one high-entropy opaque API key for machine clients."""
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(API_KEY_RANDOM_BYTES)}"


def hash_api_key(raw_api_key: str) -> str:
    """Hash a raw API key before storage or lookup."""
    return hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()


def extract_key_prefix(raw_api_key: str) -> str:
    """Return a short non-secret prefix suitable for identifying a key later."""
    stripped = raw_api_key.strip()
    if not stripped:
        return ""
    prefix_length = len(API_KEY_PREFIX) + DISPLAY_PREFIX_BODY_CHARS
    return stripped[:prefix_length]


def verify_api_key_hash(raw_api_key: str, stored_hash: str) -> bool:
    """Compare a raw API key to a stored hash without leaking timing details."""
    return hmac.compare_digest(hash_api_key(raw_api_key), stored_hash)

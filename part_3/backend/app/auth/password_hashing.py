"""Password hashing helpers for local database-backed authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass


PASSWORD_ALGORITHM = "pbkdf2_hmac_sha256"
DEFAULT_PASSWORD_ITERATIONS = 210_000
SALT_BYTES = 32


@dataclass(frozen=True)
class PasswordHashConfig:
    """Stored password-hash metadata."""

    password_hash: str
    password_salt: str
    password_algorithm: str
    password_iterations: int


def _derive_password_hash(password: str, salt: bytes, iterations: int) -> str:
    """Return a base64 PBKDF2-HMAC-SHA256 hash for a password and salt."""
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return base64.b64encode(derived).decode("ascii")


def hash_password(password: str, *, iterations: int = DEFAULT_PASSWORD_ITERATIONS) -> PasswordHashConfig:
    """Hash a raw password with a per-user random salt.

    The raw password is never returned. The returned fields are intended for
    storage in auth_users.
    """
    if iterations <= 0:
        raise ValueError("password hash iterations must be positive")
    salt = secrets.token_bytes(SALT_BYTES)
    encoded_salt = base64.b64encode(salt).decode("ascii")
    return PasswordHashConfig(
        password_hash=_derive_password_hash(password, salt, iterations),
        password_salt=encoded_salt,
        password_algorithm=PASSWORD_ALGORITHM,
        password_iterations=iterations,
    )


def verify_password(
    password: str,
    *,
    stored_hash: str,
    stored_salt: str,
    algorithm: str,
    iterations: int,
) -> bool:
    """Verify a raw password against stored password-hash metadata."""
    if algorithm != PASSWORD_ALGORITHM or iterations <= 0:
        return False

    try:
        salt = base64.b64decode(stored_salt.encode("ascii"), validate=True)
    except Exception:
        return False

    candidate_hash = _derive_password_hash(password, salt, iterations)
    return hmac.compare_digest(candidate_hash, stored_hash)

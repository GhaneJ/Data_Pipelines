"""Unit tests for password hashing and opaque access-token helpers."""

from __future__ import annotations

from datetime import timedelta

from backend.app.auth.password_hashing import PASSWORD_ALGORITHM, hash_password, verify_password
from backend.app.auth.tokens import generate_access_token, hash_access_token, is_token_expired, utc_now


def test_password_can_be_verified_against_stored_hash() -> None:
    record = hash_password("admin-password")

    assert verify_password(
        "admin-password",
        stored_hash=record.password_hash,
        stored_salt=record.password_salt,
        algorithm=record.password_algorithm,
        iterations=record.password_iterations,
    )


def test_wrong_password_fails_verification() -> None:
    record = hash_password("admin-password")

    assert not verify_password(
        "wrong-password",
        stored_hash=record.password_hash,
        stored_salt=record.password_salt,
        algorithm=record.password_algorithm,
        iterations=record.password_iterations,
    )


def test_raw_password_is_not_stored_as_hash() -> None:
    record = hash_password("admin-password")

    assert record.password_hash != "admin-password"
    assert record.password_salt != "admin-password"
    assert record.password_algorithm == PASSWORD_ALGORITHM
    assert record.password_iterations > 0


def test_different_salts_create_different_hashes() -> None:
    first = hash_password("same-password")
    second = hash_password("same-password")

    assert first.password_salt != second.password_salt
    assert first.password_hash != second.password_hash


def test_verification_uses_stored_algorithm_iterations_and_salt() -> None:
    record = hash_password("admin-password")

    assert not verify_password(
        "admin-password",
        stored_hash=record.password_hash,
        stored_salt=record.password_salt,
        algorithm="unknown",
        iterations=record.password_iterations,
    )
    assert not verify_password(
        "admin-password",
        stored_hash=record.password_hash,
        stored_salt=record.password_salt,
        algorithm=record.password_algorithm,
        iterations=0,
    )


def test_generated_access_tokens_are_random_and_not_stored_raw() -> None:
    first = generate_access_token()
    second = generate_access_token()

    assert first != second
    assert hash_access_token(first) != first
    assert hash_access_token(first) != hash_access_token(second)


def test_expiry_helper_detects_expired_tokens() -> None:
    assert is_token_expired(utc_now() - timedelta(seconds=1))
    assert not is_token_expired(utc_now() + timedelta(minutes=5))

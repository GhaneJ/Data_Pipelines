"""In-memory auth/API-key database doubles for focused tests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.app.api_keys.key_utils import extract_key_prefix, hash_api_key
from backend.app.api_keys.repositories import serialize_scopes
from backend.app.auth.models import Role
from backend.app.auth.password_hashing import hash_password
from backend.app.auth.tokens import hash_access_token, utc_now


class FakeAuthCursor:
    """Cursor double that handles auth and API-key repository SQL used by tests."""

    def __init__(self, conn: "FakeAuthConnection") -> None:
        self.conn = conn
        self._one: dict[str, Any] | None = None
        self._all: list[dict[str, Any]] = []
        self.rowcount = 0

    def __enter__(self) -> "FakeAuthCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        params = params or {}
        normalized_sql = " ".join(sql.lower().split())
        self._one = None
        self._all = []
        self.rowcount = 0
        self.conn.executed.append((sql, params))

        if "from auth_users where username" in normalized_sql:
            self._one = self.conn.users_by_username.get(str(params["username"]).lower())
            return

        if "from auth_users where id" in normalized_sql:
            self._one = next((user for user in self.conn.users_by_username.values() if str(user["id"]) == str(params["user_id"])), None)
            return

        if "insert into auth_users" in normalized_sql:
            row = {
                "id": params["id"],
                "username": params["username"],
                "display_name": params["display_name"],
                "role": params["role"],
                "provider_id": params.get("provider_id"),
                "password_hash": params["password_hash"],
                "password_salt": params["password_salt"],
                "password_algorithm": params["password_algorithm"],
                "password_iterations": params["password_iterations"],
                "is_active": True,
                "failed_login_count": 0,
                "locked_until": None,
                "last_login_at": None,
                "password_changed_at": utc_now(),
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self.conn.users_by_username[row["username"]] = row
            self._one = row
            self.rowcount = 1
            return

        if "failed_login_count = failed_login_count + 1" in normalized_sql:
            user = self.conn.user_by_id(str(params["user_id"]))
            if user:
                user["failed_login_count"] += 1
                user["updated_at"] = utc_now()
                if "locked_until" in params and user["failed_login_count"] >= int(params.get("lock_threshold", 999999)):
                    user["locked_until"] = params["locked_until"]
                self.rowcount = 1
            return

        if "set failed_login_count = 0" in normalized_sql:
            user = self.conn.user_by_id(str(params["user_id"]))
            if user:
                user["failed_login_count"] = 0
                user["locked_until"] = None
                user["last_login_at"] = utc_now()
                user["updated_at"] = utc_now()
                self.rowcount = 1
            return

        if "insert into auth_access_tokens" in normalized_sql:
            row = {
                "id": params["id"],
                "user_id": params["user_id"],
                "token_hash": params["token_hash"],
                "created_at": utc_now(),
                "expires_at": params["expires_at"],
                "revoked_at": None,
                "last_used_at": None,
            }
            self.conn.tokens_by_hash[row["token_hash"]] = row
            self._one = {k: v for k, v in row.items() if k != "token_hash"}
            self.rowcount = 1
            return

        if "from auth_access_tokens t join auth_users u" in normalized_sql:
            token = self.conn.tokens_by_hash.get(str(params["token_hash"]))
            if token:
                user = self.conn.user_by_id(str(token["user_id"]))
                if user:
                    self._one = {
                        "token_id": token["id"],
                        "user_id": token["user_id"],
                        "expires_at": token["expires_at"],
                        "revoked_at": token["revoked_at"],
                        "last_used_at": token["last_used_at"],
                        **user,
                    }
            return

        if "set last_used_at = now()" in normalized_sql and "auth_access_tokens" in normalized_sql:
            token = self.conn.token_by_id(str(params["token_id"]))
            if token:
                token["last_used_at"] = utc_now()
                self.rowcount = 1
            return

        if "set revoked_at = now()" in normalized_sql and "where token_hash" in normalized_sql:
            token = self.conn.tokens_by_hash.get(str(params["token_hash"]))
            if token and token["revoked_at"] is None:
                token["revoked_at"] = utc_now()
                self._one = {"id": token["id"]}
                self.rowcount = 1
            return

        if "set revoked_at = now()" in normalized_sql and "where user_id" in normalized_sql:
            count = 0
            for token in self.conn.tokens_by_hash.values():
                if str(token["user_id"]) == str(params["user_id"]) and token["revoked_at"] is None:
                    token["revoked_at"] = utc_now()
                    count += 1
            self.rowcount = count
            return

        if "insert into api_keys" in normalized_sql:
            row = {
                "id": params["id"],
                "name": params["name"],
                "description": params.get("description"),
                "key_prefix": params["key_prefix"],
                "key_hash": params["key_hash"],
                "scopes": params["scopes"],
                "is_active": True,
                "expires_at": params.get("expires_at"),
                "revoked_at": None,
                "revoked_by_user_id": None,
                "created_by_user_id": params["created_by_user_id"],
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "last_used_at": None,
            }
            self.conn.api_keys_by_hash[row["key_hash"]] = row
            self.conn.api_keys_by_id[str(row["id"])] = row
            self._one = {k: v for k, v in row.items() if k != "key_hash"}
            self.rowcount = 1
            return

        if "from api_keys" in normalized_sql and "where key_hash" in normalized_sql:
            row = self.conn.api_keys_by_hash.get(str(params["key_hash"]))
            if row and row["is_active"] and row["revoked_at"] is None:
                expires_at = row.get("expires_at")
                if expires_at is None or expires_at > utc_now():
                    self._one = {k: v for k, v in row.items() if k != "key_hash"}
            return

        if "from api_keys" in normalized_sql and "order by created_at" in normalized_sql:
            rows = sorted(self.conn.api_keys_by_id.values(), key=lambda row: (row["created_at"], row["name"]), reverse=True)
            self._all = [{k: v for k, v in row.items() if k != "key_hash"} for row in rows]
            return

        if "update api_keys" in normalized_sql and "set last_used_at = now()" in normalized_sql:
            row = self.conn.api_keys_by_id.get(str(params["key_id"]))
            if row:
                row["last_used_at"] = utc_now()
                row["updated_at"] = utc_now()
                self.rowcount = 1
            return

        if "update api_keys" in normalized_sql and "set is_active = false" in normalized_sql:
            row = self.conn.api_keys_by_id.get(str(params["key_id"]))
            if row:
                row["is_active"] = False
                row["revoked_at"] = row["revoked_at"] or utc_now()
                row["revoked_by_user_id"] = row["revoked_by_user_id"] or params.get("revoked_by_user_id")
                row["updated_at"] = utc_now()
                self._one = {k: v for k, v in row.items() if k != "key_hash"}
                self.rowcount = 1
            return

        # Seeder SQL and unrelated mocked route SQL are recorded but otherwise ignored.

    def executemany(self, sql: str, rows: object) -> None:
        self.conn.executed_many.append((sql, tuple(rows)))

    def fetchone(self) -> dict[str, Any] | None:
        return self._one

    def fetchall(self) -> list[dict[str, Any]]:
        return self._all


class FakeAuthConnection:
    """In-memory auth/API-key DB used by route and repository tests."""

    def __init__(self) -> None:
        self.users_by_username: dict[str, dict[str, Any]] = {}
        self.tokens_by_hash: dict[str, dict[str, Any]] = {}
        self.api_keys_by_hash: dict[str, dict[str, Any]] = {}
        self.api_keys_by_id: dict[str, dict[str, Any]] = {}
        self.executed: list[tuple[str, dict[str, Any] | None]] = []
        self.executed_many: list[tuple[str, tuple[object, ...]]] = []

    def cursor(self) -> FakeAuthCursor:
        return FakeAuthCursor(self)

    def user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return next((user for user in self.users_by_username.values() if str(user["id"]) == user_id), None)

    def token_by_id(self, token_id: str) -> dict[str, Any] | None:
        return next((token for token in self.tokens_by_hash.values() if str(token["id"]) == token_id), None)

    def add_user(
        self,
        *,
        username: str,
        password: str,
        role: Role,
        display_name: str | None = None,
        provider_id: str | None = None,
        is_active: bool = True,
        locked_until: datetime | None = None,
        failed_login_count: int = 0,
    ) -> dict[str, Any]:
        config = hash_password(password)
        row = {
            "id": str(uuid4()),
            "username": username.strip().lower(),
            "display_name": display_name or username.title(),
            "role": role.value,
            "provider_id": provider_id,
            "password_hash": config.password_hash,
            "password_salt": config.password_salt,
            "password_algorithm": config.password_algorithm,
            "password_iterations": config.password_iterations,
            "is_active": is_active,
            "failed_login_count": failed_login_count,
            "locked_until": locked_until,
            "last_login_at": None,
            "password_changed_at": utc_now(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self.users_by_username[row["username"]] = row
        return row

    def add_token(
        self,
        *,
        username: str,
        raw_token: str,
        expires_at: datetime | None = None,
        revoked: bool = False,
    ) -> dict[str, Any]:
        user = self.users_by_username[username.strip().lower()]
        token = {
            "id": str(uuid4()),
            "user_id": user["id"],
            "token_hash": hash_access_token(raw_token),
            "created_at": utc_now(),
            "expires_at": expires_at or (utc_now() + timedelta(hours=1)),
            "revoked_at": utc_now() if revoked else None,
            "last_used_at": None,
        }
        self.tokens_by_hash[token["token_hash"]] = token
        return token

    def add_api_key(
        self,
        *,
        raw_api_key: str,
        name: str = "Local export client",
        scopes: list[str] | None = None,
        created_by_user_id: str | None = None,
        description: str | None = "Local CSV export testing",
        expires_at: datetime | None = None,
        revoked: bool = False,
        is_active: bool = True,
    ) -> dict[str, Any]:
        row = {
            "id": str(uuid4()),
            "name": name,
            "description": description,
            "key_prefix": extract_key_prefix(raw_api_key),
            "key_hash": hash_api_key(raw_api_key),
            "scopes": serialize_scopes(scopes or ["export:read"]),
            "is_active": is_active,
            "expires_at": expires_at,
            "revoked_at": utc_now() if revoked else None,
            "revoked_by_user_id": None,
            "created_by_user_id": created_by_user_id or str(uuid4()),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "last_used_at": None,
        }
        self.api_keys_by_hash[row["key_hash"]] = row
        self.api_keys_by_id[row["id"]] = row
        return row


@contextmanager
def fake_connection_provider(conn: FakeAuthConnection) -> Iterator[FakeAuthConnection]:
    """Context manager matching backend.database.open_connection shape."""
    yield conn


def override_db(conn: FakeAuthConnection):
    """Build a FastAPI dependency override yielding a fake auth/API-key connection."""

    def _override() -> Iterator[FakeAuthConnection]:
        yield conn

    return _override

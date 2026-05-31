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


        if "from providers" in normalized_sql and "where provider_id" in normalized_sql:
            provider_id = str(params["provider_id"])
            self._one = self.conn.provider_names_by_id.get(provider_id) or ({"?column?": 1} if provider_id in self.conn.valid_provider_ids else None)
            return

        if "from user_registration_requests" in normalized_sql and "where requested_username" in normalized_sql:
            username = str(params["username"]).lower()
            self._one = next(
                (row for row in self.conn.registration_requests_by_id.values() if row["requested_username"] == username and row["status"] == "pending"),
                None,
            )
            return

        if "insert into user_registration_requests" in normalized_sql:
            row = {
                "id": params["id"],
                "requested_username": params["requested_username"],
                "display_name": params["display_name"],
                "email": params.get("email"),
                "provider_id": params["provider_id"],
                "requested_role": "provider",
                "organization_name": params.get("organization_name"),
                "message": params.get("message"),
                "pending_password_hash": params["pending_password_hash"],
                "pending_password_salt": params["pending_password_salt"],
                "pending_password_algorithm": params["pending_password_algorithm"],
                "pending_password_iterations": params["pending_password_iterations"],
                "status": "pending",
                "created_at": utc_now(),
                "reviewed_by_user_id": None,
                "reviewed_at": None,
                "review_notes": None,
                "created_user_id": None,
            }
            self.conn.registration_requests_by_id[row["id"]] = row
            self._one = {k: v for k, v in row.items() if not k.startswith("pending_password")}
            self.rowcount = 1
            return

        if "from user_registration_requests" in normalized_sql and "where id" in normalized_sql:
            row = self.conn.registration_requests_by_id.get(str(params["id"]))
            if row:
                self._one = dict(row) if "pending_password_hash" in normalized_sql else {k: v for k, v in row.items() if not k.startswith("pending_password")}
            return

        if "from user_registration_requests" in normalized_sql and "order by created_at" in normalized_sql:
            rows = list(self.conn.registration_requests_by_id.values())
            if "where status" in normalized_sql:
                rows = [row for row in rows if row["status"] == params["status"]]
            rows.sort(key=lambda row: (row["created_at"], row["requested_username"]), reverse=True)
            self._all = [{k: v for k, v in row.items() if not k.startswith("pending_password")} for row in rows[int(params.get("offset", 0)): int(params.get("offset", 0)) + int(params.get("limit", len(rows)))]]
            return

        if "update user_registration_requests" in normalized_sql and "set status = 'approved'" in normalized_sql:
            row = self.conn.registration_requests_by_id.get(str(params["id"]))
            if row:
                row["status"] = "approved"
                row["reviewed_by_user_id"] = params["reviewed_by_user_id"]
                row["reviewed_at"] = utc_now()
                row["review_notes"] = params.get("review_notes")
                row["created_user_id"] = params.get("created_user_id")
                self._one = {k: v for k, v in row.items() if not k.startswith("pending_password")}
                self.rowcount = 1
            return

        if "update user_registration_requests" in normalized_sql and "set status = 'rejected'" in normalized_sql:
            row = self.conn.registration_requests_by_id.get(str(params["id"]))
            if row:
                row["status"] = "rejected"
                row["reviewed_by_user_id"] = params["reviewed_by_user_id"]
                row["reviewed_at"] = utc_now()
                row["review_notes"] = params.get("review_notes")
                self._one = {k: v for k, v in row.items() if not k.startswith("pending_password")}
                self.rowcount = 1
            return

        if "from auth_users" in normalized_sql and "order by created_at" in normalized_sql:
            rows = list(self.conn.users_by_username.values())
            if "role =" in normalized_sql:
                rows = [row for row in rows if row["role"] == params["role"]]
            if "is_active =" in normalized_sql:
                rows = [row for row in rows if row["is_active"] == params["is_active"]]
            if "ilike" in normalized_sql:
                needle = str(params["search"]).strip("%").lower()
                rows = [row for row in rows if needle in row["username"].lower() or needle in row["display_name"].lower() or needle in str(row.get("provider_id") or "").lower()]
            rows.sort(key=lambda row: (row["created_at"], row["username"]), reverse=True)
            self._all = [dict(row) for row in rows[int(params.get("offset", 0)): int(params.get("offset", 0)) + int(params.get("limit", len(rows)))]]
            return

        if "update auth_users" in normalized_sql and "set display_name" in normalized_sql:
            user = self.conn.user_by_id(str(params["user_id"]))
            if user:
                user["display_name"] = params["display_name"]
                user["role"] = params["role"]
                user["provider_id"] = params.get("provider_id")
                user["is_active"] = params["is_active"]
                user["updated_at"] = utc_now()
                self._one = dict(user)
                self.rowcount = 1
            return

        if "update auth_users" in normalized_sql and "set password_hash" in normalized_sql:
            user = self.conn.user_by_id(str(params["user_id"]))
            if user:
                user["password_hash"] = params["password_hash"]
                user["password_salt"] = params["password_salt"]
                user["password_algorithm"] = params["password_algorithm"]
                user["password_iterations"] = params["password_iterations"]
                user["password_changed_at"] = utc_now()
                user["failed_login_count"] = 0
                user["locked_until"] = None
                user["updated_at"] = utc_now()
                self._one = dict(user)
                self.rowcount = 1
            return

        if "update auth_users" in normalized_sql and "set is_active" in normalized_sql:
            user = self.conn.user_by_id(str(params["user_id"]))
            if user:
                user["is_active"] = params["is_active"]
                user["updated_at"] = utc_now()
                self.rowcount = 1
            return

        if "from auth_access_tokens" in normalized_sql and "where user_id" in normalized_sql and "order by created_at" in normalized_sql:
            rows = [dict(token) for token in self.conn.tokens_by_hash.values() if str(token["user_id"]) == str(params["user_id"])]
            for row in rows:
                row.pop("token_hash", None)
                row["is_active"] = row["revoked_at"] is None and row["expires_at"] > utc_now()
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            self._all = rows
            return

        if "update auth_access_tokens" in normalized_sql and "where id" in normalized_sql and "user_id" in normalized_sql:
            token = self.conn.token_by_id(str(params["session_id"]))
            if token and str(token["user_id"]) == str(params["user_id"]) and token["revoked_at"] is None:
                token["revoked_at"] = utc_now()
                self._one = {"id": token["id"]}
                self.rowcount = 1
            return

        if "insert into auth_admin_events" in normalized_sql:
            self.conn.admin_events.append(dict(params))
            self.rowcount = 1
            return

        if "insert into provider_application_submissions" in normalized_sql:
            row = {
                "id": params["id"],
                "provider_id": params["provider_id"],
                "provider_name": params.get("provider_name"),
                "created_by_user_id": params["created_by_user_id"],
                "status": params["status"],
                "target_year": params.get("target_year"),
                "education_name": params["education_name"],
                "education_area": params.get("education_area"),
                "municipality": params.get("municipality"),
                "region": params.get("region"),
                "yh_points": params.get("yh_points"),
                "study_form": params.get("study_form"),
                "study_pace_percent": params.get("study_pace_percent"),
                "head_provider_type": params.get("head_provider_type"),
                "description": params.get("description"),
                "notes": params.get("notes"),
                "submitted_at": None,
                "review_started_at": None,
                "reviewed_by_user_id": None,
                "reviewed_at": None,
                "review_notes": None,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self.conn.provider_submissions_by_id[str(row["id"])] = row
            self._one = dict(row)
            self.rowcount = 1
            return

        if "insert into provider_submission_review_events" in normalized_sql:
            row = {
                "id": params["id"],
                "submission_id": params["submission_id"],
                "actor_user_id": params.get("actor_user_id"),
                "actor_role": params["actor_role"],
                "action": params["action"],
                "from_status": params.get("from_status"),
                "to_status": params["to_status"],
                "notes": params.get("notes"),
                "created_at": utc_now(),
            }
            self.conn.review_events_by_id[str(row["id"])] = row
            self._one = dict(row)
            self.rowcount = 1
            return

        if normalized_sql.startswith("select") and "from provider_application_submissions" in normalized_sql and "where id" in normalized_sql:
            row = self.conn.provider_submissions_by_id.get(str(params["id"]))
            if row and ("provider_id" not in params or row["provider_id"] == str(params["provider_id"])):
                self._one = dict(row)
            return

        if normalized_sql.startswith("select") and "from provider_application_submissions" in normalized_sql and "order by submitted_at" in normalized_sql:
            rows = [dict(row) for row in self.conn.provider_submissions_by_id.values()]
            if params.get("default_statuses") is not None:
                rows = [row for row in rows if row["status"] in set(params["default_statuses"])]
            if params.get("status") is not None:
                rows = [row for row in rows if row["status"] == str(params["status"])]
            if params.get("provider_id") is not None:
                rows = [row for row in rows if row["provider_id"] == str(params["provider_id"])]
            if params.get("target_year") is not None:
                rows = [row for row in rows if row["target_year"] == params["target_year"]]
            rows.sort(key=lambda row: (row["submitted_at"] or row["created_at"], row["created_at"], str(row["id"])), reverse=True)
            offset = int(params.get("offset", 0))
            limit = int(params.get("limit", len(rows)))
            self._all = rows[offset : offset + limit]
            return

        if normalized_sql.startswith("select") and "from provider_application_submissions" in normalized_sql and "order by created_at" in normalized_sql:
            rows = [
                dict(row)
                for row in self.conn.provider_submissions_by_id.values()
                if row["provider_id"] == str(params["provider_id"])
            ]
            if params.get("status") is not None:
                rows = [row for row in rows if row["status"] == str(params["status"])]
            if params.get("target_year") is not None:
                rows = [row for row in rows if row["target_year"] == params["target_year"]]
            rows.sort(key=lambda row: (row["created_at"], str(row["id"])), reverse=True)
            offset = int(params.get("offset", 0))
            limit = int(params.get("limit", len(rows)))
            self._all = rows[offset : offset + limit]
            return

        if normalized_sql.startswith("select") and "from provider_submission_review_events" in normalized_sql:
            rows = [
                dict(row)
                for row in self.conn.review_events_by_id.values()
                if str(row["submission_id"]) == str(params["submission_id"])
            ]
            rows.sort(key=lambda row: (row["created_at"], str(row["id"])))
            self._all = rows
            return

        if "update provider_application_submissions" in normalized_sql and "reviewed_by_user_id" in normalized_sql and "from_status" in params:
            row = self.conn.provider_submissions_by_id.get(str(params["id"]))
            if row and row["status"] == str(params["from_status"]):
                row["status"] = params["to_status"]
                row["review_started_at"] = row["review_started_at"] or utc_now()
                row["reviewed_by_user_id"] = params.get("admin_user_id")
                if "reviewed_at = now()" in normalized_sql:
                    row["reviewed_at"] = utc_now()
                row["review_notes"] = params.get("review_notes")
                row["updated_at"] = utc_now()
                self._one = dict(row)
                self.rowcount = 1
            return

        if "update provider_application_submissions" in normalized_sql and "set status = 'submitted'" in normalized_sql:
            row = self.conn.provider_submissions_by_id.get(str(params["id"]))
            if row and row["provider_id"] == str(params["provider_id"]) and row["status"] in {"draft", "needs_changes"}:
                row["status"] = "submitted"
                row["submitted_at"] = utc_now()
                row["updated_at"] = utc_now()
                self._one = dict(row)
                self.rowcount = 1
            return

        if "update provider_application_submissions" in normalized_sql:
            row = self.conn.provider_submissions_by_id.get(str(params["id"]))
            if row and row["provider_id"] == str(params["provider_id"]) and row["status"] in {"draft", "needs_changes"}:
                for field in (
                    "target_year",
                    "education_name",
                    "education_area",
                    "municipality",
                    "region",
                    "yh_points",
                    "study_form",
                    "study_pace_percent",
                    "head_provider_type",
                    "description",
                    "notes",
                ):
                    if field in params:
                        row[field] = params[field]
                row["updated_at"] = utc_now()
                self._one = dict(row)
                self.rowcount = 1
            return

        if "delete from provider_application_submissions" in normalized_sql:
            row = self.conn.provider_submissions_by_id.get(str(params["id"]))
            if row and row["provider_id"] == str(params["provider_id"]) and row["status"] == "draft":
                removed = self.conn.provider_submissions_by_id.pop(str(params["id"]))
                self._one = {"id": removed["id"]}
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
        self.provider_submissions_by_id: dict[str, dict[str, Any]] = {}
        self.review_events_by_id: dict[str, dict[str, Any]] = {}
        self.provider_names_by_id: dict[str, dict[str, str]] = {"999999": {"utbildningsanordnare": "Local Provider"}}
        self.valid_provider_ids: set[str] = {"999999"}
        self.registration_requests_by_id: dict[str, dict[str, Any]] = {}
        self.admin_events: list[dict[str, Any]] = []
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


    def add_provider_name(self, provider_id: str, provider_name: str) -> dict[str, str]:
        row = {"utbildningsanordnare": provider_name}
        self.provider_names_by_id[str(provider_id)] = row
        self.valid_provider_ids.add(str(provider_id))
        return row

    def add_registration_request(
        self,
        *,
        requested_username: str = "new-provider",
        display_name: str = "New Provider",
        password: str = "NewProvider1!",
        provider_id: str = "999999",
        status: str = "pending",
    ) -> dict[str, Any]:
        config = hash_password(password)
        row = {
            "id": str(uuid4()),
            "requested_username": requested_username.strip().lower(),
            "display_name": display_name,
            "email": None,
            "provider_id": provider_id,
            "requested_role": "provider",
            "organization_name": None,
            "message": "Local test request",
            "pending_password_hash": config.password_hash,
            "pending_password_salt": config.password_salt,
            "pending_password_algorithm": config.password_algorithm,
            "pending_password_iterations": config.password_iterations,
            "status": status,
            "created_at": utc_now(),
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "review_notes": None,
            "created_user_id": None,
        }
        self.registration_requests_by_id[row["id"]] = row
        return row

    def add_provider_submission(
        self,
        *,
        provider_id: str = "999999",
        provider_name: str | None = "Local Provider",
        created_by_user_id: str | None = None,
        status: str = "draft",
        target_year: int | None = 2026,
        education_name: str = "Cloud Data Engineer",
        education_area: str | None = "Data/IT",
        municipality: str | None = "Stockholm",
        region: str | None = "Stockholms län",
        yh_points: int | None = 400,
        study_form: str | None = "Distans",
        study_pace_percent: int | None = 100,
        head_provider_type: str | None = "Privat",
        description: str | None = "Provider-created draft application for future review.",
        notes: str | None = "Initial local validation draft.",
    ) -> dict[str, Any]:
        created_at = utc_now()
        row = {
            "id": str(uuid4()),
            "provider_id": provider_id,
            "provider_name": provider_name,
            "created_by_user_id": created_by_user_id or str(uuid4()),
            "status": status,
            "target_year": target_year,
            "education_name": education_name,
            "education_area": education_area,
            "municipality": municipality,
            "region": region,
            "yh_points": yh_points,
            "study_form": study_form,
            "study_pace_percent": study_pace_percent,
            "head_provider_type": head_provider_type,
            "description": description,
            "notes": notes,
            "submitted_at": created_at if status != "draft" else None,
            "review_started_at": created_at if status in {"under_review", "needs_changes", "approved", "rejected"} else None,
            "reviewed_by_user_id": None,
            "reviewed_at": created_at if status in {"needs_changes", "approved", "rejected"} else None,
            "review_notes": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
        self.provider_submissions_by_id[row["id"]] = row
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

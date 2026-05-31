"""Print and optionally check a concise final-demo flow for the API.

The smoke test is for validation. This script is for presentation readiness:
it shows the endpoint sequence, why each endpoint matters, and a short result
summary when the API is running locally.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DemoStep:
    """One endpoint in the suggested final API demonstration flow."""

    title: str
    method: str
    path: str
    purpose: str
    response_kind: str = "json"
    call_by_default: bool = True


def fetch_json(method: str, url: str) -> Any:
    """Call one JSON endpoint and return parsed data."""
    request = Request(url, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_csv(url: str, api_key: str | None = None) -> list[dict[str, str]]:
    """Call one CSV endpoint and return parsed rows."""
    headers = {"X-API-Key": api_key} if api_key else {}
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=10) as response:
        csv_text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(csv_text)))


def summarize_json(data: Any) -> str:
    """Create a small human-readable summary of a JSON response."""
    if isinstance(data, dict) and "items" in data:
        return f"total={data.get('total')}, returned_items={len(data.get('items', []))}"

    if isinstance(data, dict) and "diarienummer" in data:
        return (
            f"diarienummer={data.get('diarienummer')}, "
            f"year={data.get('source_year')}, decision={data.get('beslut_normalized')}"
        )

    if isinstance(data, dict):
        keys = ", ".join(sorted(data)[:5])
        return f"object with fields: {keys}"

    if isinstance(data, list):
        if not data:
            return "empty list"
        keys = ", ".join(sorted(data[0])[:5]) if isinstance(data[0], dict) else type(data[0]).__name__
        return f"rows={len(data)}, first row fields: {keys}"

    return type(data).__name__


def print_step(number: int, step: DemoStep, url: str, result: str | None = None) -> None:
    """Print one demo step in a compact, repeatable format."""
    print(f"{number}. {step.title}")
    print(f"   Purpose: {step.purpose}")
    print(f"   Request: {step.method} {url}")
    if result:
        print(f"   Result: {result}")
    print()


def main() -> None:
    """Print or run a concise endpoint sequence for the final presentation."""
    parser = argparse.ArgumentParser(description="Show a final demo flow for the MYH Applications API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the running API.")
    parser.add_argument("--print-only", action="store_true", help="Only print the demo flow; do not call the API.")
    parser.add_argument("--api-key", help="Database-issued API key with export:read scope for calling the protected CSV export step.")
    parser.add_argument("--include-refresh", action="store_true", help="Also call POST /refresh at the end of the demo flow.")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    print("MYH Applications API — suggested final demo flow")
    print("=" * 58)
    print("Start uvicorn first, then run this script from part_3.")
    print()

    first_diarienummer: str | None = None
    first_provider_id: int | None = None

    steps: list[DemoStep] = [
        DemoStep("Service landing page", "GET", "/", "Shows that the FastAPI service is running."),
        DemoStep("Health check", "GET", "/health", "Quick operational check for local validation."),
        DemoStep("Database readiness", "GET", "/health/db", "Checks database connection, required tables, and loaded rows."),
        DemoStep(
            "Source-check status",
            "GET",
            "/operations/source-status",
            "Shows the last recorded MYH source-page check without changing application data.",
        ),
        DemoStep(
            "Manual source check",
            "POST",
            "/operations/check-source",
            "Checks the configured MYH source page and writes the local manifest; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Protected admin notes",
            "POST",
            "/admin/applications/{diarienummer}/notes",
            "Creates local admin metadata for one application using a database-issued admin bearer token; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Protected admin note list",
            "GET",
            "/admin/applications/{diarienummer}/notes",
            "Reads local admin notes using a database-issued admin bearer token; note text remains under protected /admin routes.",
            call_by_default=False,
        ),
        DemoStep(
            "Protected admin note patch",
            "PATCH",
            "/admin/notes/{note_id}",
            "Partially updates local admin-note metadata using a database-issued admin bearer token; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin API key creation",
            "POST",
            "/admin/api-keys",
            "Creates a database-backed machine API key using an admin bearer token; the raw key is returned once only.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin API key list",
            "GET",
            "/admin/api-keys",
            "Lists safe API key metadata without raw keys or hashes.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin API key revoke",
            "POST",
            "/admin/api-keys/{api_key_id}/revoke",
            "Revokes a machine API key so it can no longer access protected export endpoints.",
            call_by_default=False,
        ),
        DemoStep(
            "Provider access request",
            "POST",
            "/auth/registration-requests",
            "Creates a pending provider access request from the public signup form; it does not create an active login by itself.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin registration request list",
            "GET",
            "/admin/registration-requests",
            "Lists controlled signup requests for admin approval/rejection using an admin bearer token; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin registration request approve",
            "POST",
            "/admin/registration-requests/{request_id}/approve",
            "Approves a pending provider request and creates the real active provider user; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin user list",
            "GET",
            "/admin/users",
            "Lists safe admin/provider user metadata without password hashes or session token hashes; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin user create",
            "POST",
            "/admin/users",
            "Creates an admin or provider user through admin-only user management; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin session revoke",
            "POST",
            "/admin/users/{user_id}/sessions/{session_id}/revoke",
            "Revokes one database-issued bearer session through admin-only session management; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Provider login",
            "POST",
            "/auth/login",
            "Creates a database-issued provider bearer session for provider submission CRUD; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Provider submission create",
            "POST",
            "/provider/submissions",
            "Creates a provider-owned draft application submission using Authorization: Bearer <provider-token>; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Provider submission list",
            "GET",
            "/provider/submissions",
            "Lists only the authenticated provider's own submissions; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Provider submission update",
            "PATCH",
            "/provider/submissions/{submission_id}",
            "Updates editable fields only while the submission is still draft; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Provider submission submit",
            "POST",
            "/provider/submissions/{submission_id}/submit",
            "Moves a draft or needs_changes submission to submitted for admin review; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin review queue",
            "GET",
            "/admin/provider-submissions",
            "Lists submitted/under-review/needs-changes provider submissions using Authorization: Bearer <admin-token>; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin review detail",
            "GET",
            "/admin/provider-submissions/{submission_id}",
            "Reads any provider submission with review metadata using an admin bearer token; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin start review",
            "POST",
            "/admin/provider-submissions/{submission_id}/start-review",
            "Moves a submitted provider submission to under_review; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin request changes",
            "POST",
            "/admin/provider-submissions/{submission_id}/request-changes",
            "Returns a submitted/under_review provider submission to the provider with review notes; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin approve submission",
            "POST",
            "/admin/provider-submissions/{submission_id}/approve",
            "Approves the provider submission as workflow state only; it does not mutate historical applications; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Admin review events",
            "GET",
            "/admin/provider-submissions/{submission_id}/events",
            "Reads ordered status-transition history for one provider submission; not called by default.",
            call_by_default=False,
        ),
        DemoStep(
            "Filtered application browsing",
            "GET",
            "/applications?" + urlencode({"source_year": 2024, "decision": "approved", "limit": 3}),
            "Shows record browsing, useful filters, and pagination metadata.",
        ),
        DemoStep("Application detail", "GET", "", "Fetches one record by natural diarienummer identifier."),
        DemoStep("Yearly statistics", "GET", "/stats/by-year", "Shows SQL aggregation by source year."),
        DemoStep("Regional statistics", "GET", "/stats/by-region", "Shows grouped statistics by län/region."),
        DemoStep("Education-area statistics", "GET", "/stats/by-education-area", "Shows grouped statistics by education area."),
        DemoStep("Decision statistics", "GET", "/stats/by-decision", "Shows distribution of normalized decisions."),
        DemoStep(
            "Decision trend",
            "GET",
            "/stats/trends/by-decision?" + urlencode({"year_from": 2020, "year_to": 2025}),
            "Shows development over time without the consumer grouping raw records.",
        ),
        DemoStep(
            "Top regional trends",
            "GET",
            "/stats/trends/by-region?" + urlencode({"year_from": 2023, "year_to": 2025, "limit": 5}),
            "Shows chart-friendly yearly counts for top regions.",
        ),
        DemoStep(
            "Provider browsing",
            "GET",
            "/providers?" + urlencode({"limit": 5}),
            "Shows provider browsing with stable numeric provider IDs.",
        ),
        DemoStep("Provider applications", "GET", "", "Uses a provider_id from /providers to browse that provider's applications."),
        DemoStep(
            "Filtered CSV export",
            "GET",
            "/export/applications?" + urlencode({"year": 2024, "decision": "approved", "limit": 10}),
            "Shows the API can return a downloadable filtered dataset when X-API-Key has export:read scope.",
            response_kind="csv",
        ),
        DemoStep("Interactive API docs", "GET", "/docs", "Open this in the browser to show FastAPI/OpenAPI documentation.", call_by_default=False),
        DemoStep("Operational refresh", "POST", "/refresh", "Reloads PostgreSQL from the existing curated CSV.", call_by_default=False),
    ]

    for index, step in enumerate(steps, start=1):
        if step.title == "Application detail":
            path = f"/applications/{quote(first_diarienummer, safe='')}" if first_diarienummer else "/applications/{diarienummer}"
        elif step.title == "Provider applications":
            path = f"/providers/{first_provider_id}/applications?limit=3" if first_provider_id else "/providers/{provider_id}/applications?limit=3"
        else:
            path = step.path

        url = f"{base_url}{path}"

        should_call = step.call_by_default and not args.print_only
        if step.title == "Filtered CSV export" and not args.api_key:
            should_call = False
        if step.title == "Operational refresh" and args.include_refresh and not args.print_only:
            should_call = True

        if not should_call:
            extra = None
            if step.title == "Interactive API docs":
                extra = "open in browser"
            elif step.title == "Manual source check":
                extra = "not called by default; run from /docs or use the check_source_status.py script"
            elif step.title in {
                "Protected admin notes",
                "Protected admin note list",
                "Protected admin note patch",
                "Admin API key creation",
                "Admin API key list",
                "Admin API key revoke",
                "Admin registration request list",
                "Admin registration request approve",
                "Admin user list",
                "Admin user create",
                "Admin session revoke",
                "Admin review queue",
                "Admin review detail",
                "Admin start review",
                "Admin request changes",
                "Admin approve submission",
                "Admin review events",
            }:
                extra = "not called by default; log in through /auth/login and send Authorization: Bearer <admin-token> from /docs or curl"
            elif step.title == "Provider access request":
                extra = "not called by default; this is the public signup/request-access flow and creates only a pending request"
            elif step.title.startswith("Provider submission") or step.title == "Provider login":
                extra = "not called by default; log in through /auth/login and send Authorization: Bearer <provider-token> from /docs or curl"
            elif step.title == "Filtered CSV export" and not args.api_key:
                extra = "requires a database-issued X-API-Key with export:read; pass --api-key to call it"
            elif step.title == "Operational refresh" and not args.include_refresh:
                extra = "not called by default; add --include-refresh to run it"
            print_step(index, step, url, extra)
            continue

        if step.response_kind == "csv":
            rows = fetch_csv(url, api_key=args.api_key)
            columns = list(rows[0]) if rows else []
            result = f"csv_rows={len(rows)}, first_columns={columns[:6]}"
        else:
            data = fetch_json(step.method, url)
            result = summarize_json(data)
            if step.title == "Filtered application browsing":
                items = data.get("items", []) if isinstance(data, dict) else []
                first_diarienummer = items[0].get("diarienummer") if items else None
            elif step.title == "Provider browsing":
                items = data.get("items", []) if isinstance(data, dict) else []
                first_provider_id = items[0].get("provider_id") if items else None

        print_step(index, step, url, result)


if __name__ == "__main__":
    main()

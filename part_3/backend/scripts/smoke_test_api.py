"""Small smoke test for the local FastAPI read API.

Run this after starting uvicorn. It uses only the Python standard library so it
keeps the local verification workflow simple.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


EXPECTED_YEARS = {2020, 2021, 2022, 2023, 2024, 2025}
EXPECTED_DECISIONS = {"approved", "rejected", "withdrawn"}


def get_json(url: str) -> Any:
    """Fetch one API URL and parse the JSON response."""
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str) -> Any:
    """Send one POST request and parse the JSON response."""
    request = Request(url, method="POST")
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_csv_rows(url: str) -> list[dict[str, str]]:
    """Fetch one CSV export URL and return parsed rows."""
    with urlopen(url, timeout=10) as response:
        content_type = response.headers.get("Content-Type", "")
        content_disposition = response.headers.get("Content-Disposition", "")
        csv_text = response.read().decode("utf-8")

    if "text/csv" not in content_type:
        raise SystemExit(f"Expected CSV content type from {url}, got {content_type!r}.")
    if "attachment" not in content_disposition:
        raise SystemExit(f"Expected downloadable attachment response from {url}.")

    return list(csv.DictReader(io.StringIO(csv_text)))


def require_items(response: dict[str, Any], endpoint: str) -> list[dict[str, Any]]:
    """Return paginated items or stop with a useful smoke-test error."""
    items = response.get("items", [])
    if not items:
        raise SystemExit(f"Expected at least one item from {endpoint}.")
    return items


def require_trend_rows(rows: Any, endpoint: str, expected_fields: set[str]) -> list[dict[str, Any]]:
    """Check that a trend endpoint returns rows with the expected basic shape."""
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"Expected trend rows from {endpoint}.")

    missing_fields = expected_fields - set(rows[0])
    if missing_fields:
        raise SystemExit(f"Missing fields from {endpoint}: {sorted(missing_fields)}")

    return rows


def main() -> None:
    """Run read-only checks against the local API."""
    parser = argparse.ArgumentParser(description="Smoke test the local MYH Applications API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the API.")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = get_json(f"{base_url}/health")
    if health.get("status") != "ok":
        raise SystemExit(f"Unexpected health response: {health}")

    refresh = post_json(f"{base_url}/refresh")
    if refresh.get("status") != "success":
        raise SystemExit(f"Unexpected refresh response: {refresh}")
    if refresh.get("rows_loaded", 0) <= 0:
        raise SystemExit(f"Refresh did not report loaded rows: {refresh}")
    if "myh_curated_applications_2020_2025.csv" not in refresh.get("source_file", ""):
        raise SystemExit(f"Refresh response did not identify the curated CSV: {refresh}")
    if not refresh.get("refreshed_at"):
        raise SystemExit(f"Refresh response did not include refreshed_at: {refresh}")

    params = urlencode({"source_year": 2024, "decision": "approved", "limit": 3})
    applications = get_json(f"{base_url}/applications?{params}")
    application_items = require_items(applications, "/applications")

    diarienummer = application_items[0]["diarienummer"]
    detail = get_json(f"{base_url}/applications/{quote(diarienummer, safe='')}")
    if detail.get("diarienummer") != diarienummer:
        raise SystemExit("Application detail response did not match the list response.")

    yearly_stats = get_json(f"{base_url}/stats/by-year")
    years = {row["source_year"] for row in yearly_stats}
    if years != EXPECTED_YEARS:
        raise SystemExit(f"Unexpected year coverage from /stats/by-year: {sorted(years)}")

    regional_stats = get_json(f"{base_url}/stats/by-region")
    if not regional_stats or "lan" not in regional_stats[0]:
        raise SystemExit("Expected regional rows from /stats/by-region.")

    education_area_stats = get_json(f"{base_url}/stats/by-education-area")
    if not education_area_stats or "utbildningsomrade" not in education_area_stats[0]:
        raise SystemExit("Expected education-area rows from /stats/by-education-area.")

    decision_stats = get_json(f"{base_url}/stats/by-decision")
    decisions = {row["decision_code"] for row in decision_stats}
    if decisions != EXPECTED_DECISIONS:
        raise SystemExit(f"Unexpected decisions from /stats/by-decision: {sorted(decisions)}")

    decision_trend_params = urlencode({"year_from": 2024, "year_to": 2025, "decision": "approved"})
    decision_trends = require_trend_rows(
        get_json(f"{base_url}/stats/trends/by-decision?{decision_trend_params}"),
        "/stats/trends/by-decision",
        {"source_year", "decision_code", "decision_label", "application_count"},
    )
    if any(row["decision_code"] != "approved" for row in decision_trends):
        raise SystemExit("Decision trend filter returned a non-approved row.")

    region_trend_params = urlencode({"year_from": 2024, "year_to": 2025, "limit": 3})
    require_trend_rows(
        get_json(f"{base_url}/stats/trends/by-region?{region_trend_params}"),
        "/stats/trends/by-region",
        {"source_year", "lan", "application_count"},
    )

    education_trend_params = urlencode({"year_from": 2024, "year_to": 2025, "limit": 3})
    require_trend_rows(
        get_json(f"{base_url}/stats/trends/by-education-area?{education_trend_params}"),
        "/stats/trends/by-education-area",
        {"source_year", "education_area_id", "utbildningsomrade", "application_count"},
    )

    providers = get_json(f"{base_url}/providers?limit=3")
    provider_items = require_items(providers, "/providers")

    provider_id = provider_items[0]["provider_id"]
    provider_applications = get_json(f"{base_url}/providers/{provider_id}/applications?limit=3")
    require_items(provider_applications, f"/providers/{provider_id}/applications")

    export_rows = get_csv_rows(f"{base_url}/export/applications?{urlencode({'limit': 5})}")
    if not export_rows or "diarienummer" not in export_rows[0]:
        raise SystemExit("Expected CSV rows with diarienummer from /export/applications.")

    export_params = urlencode({"year": 2024, "decision": "approved", "limit": 5})
    filtered_export_rows = get_csv_rows(f"{base_url}/export/applications?{export_params}")
    if not filtered_export_rows:
        raise SystemExit("Expected filtered CSV rows from /export/applications.")
    for row in filtered_export_rows:
        if row.get("source_year") != "2024" or row.get("beslut_normalized") != "approved":
            raise SystemExit("Filtered CSV export returned a row outside year=2024 and decision=approved.")

    print("API smoke test completed successfully.")


if __name__ == "__main__":
    main()

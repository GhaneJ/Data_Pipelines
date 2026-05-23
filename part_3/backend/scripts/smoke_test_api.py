"""Small smoke test for the local FastAPI read API.

Run this after starting uvicorn. It uses only the Python standard library so it
keeps the local verification workflow simple.
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import urlopen


def get_json(url: str) -> Any:
    """Fetch one API URL and parse the JSON response."""
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    """Run a few read-only checks against the local API."""
    parser = argparse.ArgumentParser(description="Smoke test the local MYH Applications API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the API.")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = get_json(f"{base_url}/health")
    if health.get("status") != "ok":
        raise SystemExit(f"Unexpected health response: {health}")

    params = urlencode({"source_year": 2024, "decision": "approved", "limit": 3})
    applications = get_json(f"{base_url}/applications?{params}")
    if not applications.get("items"):
        raise SystemExit("Expected at least one approved 2024 application in the smoke test response.")

    diarienummer = applications["items"][0]["diarienummer"]
    detail = get_json(f"{base_url}/applications/{quote(diarienummer, safe='')}")
    if detail.get("diarienummer") != diarienummer:
        raise SystemExit("Application detail response did not match the list response.")

    yearly_stats = get_json(f"{base_url}/stats/by-year")
    years = {row["source_year"] for row in yearly_stats}
    expected_years = {2020, 2021, 2022, 2023, 2024, 2025}
    if years != expected_years:
        raise SystemExit(f"Unexpected year coverage from /stats/by-year: {sorted(years)}")

    print("API smoke test completed successfully.")


if __name__ == "__main__":
    main()

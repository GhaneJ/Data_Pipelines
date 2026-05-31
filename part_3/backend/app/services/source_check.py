"""MYH source-page checking and local status-manifest helpers.

This module intentionally keeps the source check modest. It does not download or
replace project data. It checks whether the configured MYH result page can be
reached, extracts visible Excel links when possible, compares the discovered
latest year with the local curated CSV, and writes a small JSON manifest that a
manual script or future scheduler can reuse.
"""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from backend.scripts.load_curated_data import resolve_csv_path


DEFAULT_SOURCE_URL = "https://www.myh.se/yrkeshogskolan/resultat-ansokningsomgangar/resultat-for-program"
DEFAULT_TIMEOUT_SECONDS = 15
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_DIR = BACKEND_ROOT / "runtime"
DEFAULT_MANIFEST_PATH = DEFAULT_RUNTIME_DIR / "source_status.json"
EXCEL_LINK_PATTERN = re.compile(r"href=[\"']([^\"']+\.(?:xlsx|xlsm|xls)(?:\?[^\"']*)?)[\"']", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


@dataclass(frozen=True)
class SourcePageResponse:
    """Small response object returned by the page fetcher."""

    status_code: int
    body: str
    content_type: str | None = None


@dataclass(frozen=True)
class SourceCheckConfig:
    """Configuration for one MYH source check."""

    source_url: str = DEFAULT_SOURCE_URL
    configured_files: tuple[str, ...] = ()
    manifest_path: Path = DEFAULT_MANIFEST_PATH
    local_csv_path: Path | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


def parse_configured_files(raw_value: str | None) -> tuple[str, ...]:
    """Parse a comma-separated file/URL list from configuration."""
    if not raw_value:
        return ()
    return tuple(part.strip() for part in raw_value.split(",") if part.strip())


def build_config_from_env() -> SourceCheckConfig:
    """Build source-check configuration from environment variables."""
    raw_timeout = os.getenv("MYH_SOURCE_CHECK_TIMEOUT_SECONDS")
    try:
        timeout_seconds = int(raw_timeout) if raw_timeout else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    manifest_path = Path(os.getenv("MYH_SOURCE_STATUS_PATH", str(DEFAULT_MANIFEST_PATH)))
    local_csv_value = os.getenv("MYH_CURATED_CSV_PATH")

    return SourceCheckConfig(
        source_url=os.getenv("MYH_SOURCE_URL", DEFAULT_SOURCE_URL),
        configured_files=parse_configured_files(os.getenv("MYH_SOURCE_FILES")),
        manifest_path=manifest_path,
        local_csv_path=Path(local_csv_value) if local_csv_value else None,
        timeout_seconds=timeout_seconds,
    )


def file_candidate_from_url(url: str) -> dict[str, str]:
    """Convert an absolute URL into the file-candidate shape used by the API."""
    parsed = urlparse(url)
    file_name = unquote(Path(parsed.path).name) or url
    return {"file_name": file_name, "url": url}


def file_candidate_from_config(value: str, base_url: str) -> dict[str, str | None]:
    """Convert a configured URL or file name into a file-candidate dictionary."""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return file_candidate_from_url(value)
    return {"file_name": value, "url": urljoin(base_url, value) if value.lower().startswith("/") else None}


def discover_excel_files(html: str, source_url: str) -> list[dict[str, str]]:
    """Extract visible Excel file links from a source-page HTML document."""
    discovered: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for match in EXCEL_LINK_PATTERN.finditer(html):
        absolute_url = urljoin(source_url, match.group(1))
        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)
        discovered.append(file_candidate_from_url(absolute_url))

    return discovered


def extract_latest_year(candidates: list[dict[str, Any]]) -> int | None:
    """Return the latest 20xx year visible in file names or URLs."""
    years: set[int] = set()
    for candidate in candidates:
        for value in (candidate.get("file_name"), candidate.get("url")):
            if not value:
                continue
            years.update(int(match.group(1)) for match in YEAR_PATTERN.finditer(str(value)))
    return max(years) if years else None


def read_local_latest_source_year(csv_path: Path | None = None) -> int | None:
    """Read the latest source_year from the curated CSV, if it can be found."""
    try:
        resolved_csv_path = resolve_csv_path(csv_path)
    except FileNotFoundError:
        return None

    with resolved_csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        header = file.readline().strip().split(",")
        try:
            source_year_index = header.index("source_year")
        except ValueError:
            return None

        years: set[int] = set()
        for line in file:
            # csv.reader keeps this safe even if later columns contain commas.
            values = next(csv.reader([line]))
            if len(values) <= source_year_index:
                continue
            value = values[source_year_index].strip()
            if value.isdigit():
                years.add(int(value))

    return max(years) if years else None


def fetch_source_page(source_url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> SourcePageResponse:
    """Fetch the configured source page using the Python standard library."""
    request = Request(
        source_url,
        headers={"User-Agent": "myh-applications-api-source-check/0.3.11"},
        method="GET",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
        return SourcePageResponse(
            status_code=response.getcode(),
            body=body,
            content_type=response.headers.get("Content-Type"),
        )


def build_status_message(
    *,
    status: str,
    discovered_count: int,
    configured_count: int,
    latest_source_year: int | None,
    local_latest_year: int | None,
) -> str:
    """Create a readable status message for API, CLI, and manifest output."""
    if status == "up_to_date":
        return f"Local curated data is aligned with the latest visible source year ({latest_source_year})."
    if status == "possibly_stale":
        return (
            f"The source page appears to contain year {latest_source_year}, "
            f"while the local curated data reaches {local_latest_year}. Review the source before refreshing."
        )
    if status == "local_ahead_of_source":
        return (
            f"The local curated data reaches {local_latest_year}, which is newer than the latest visible "
            f"source year ({latest_source_year}). Review manually if this is unexpected."
        )
    if discovered_count == 0 and configured_count == 0:
        return "Source page was reachable, but no Excel links were discovered automatically. Review the page manually."
    if discovered_count == 0 and configured_count > 0:
        return "Source page was reachable. No Excel links were discovered, so configured files are shown instead."
    return f"Source page was reachable and {discovered_count} Excel file candidate(s) were discovered."


def determine_status(latest_source_year: int | None, local_latest_year: int | None) -> tuple[str, bool | None]:
    """Compare source and local years in an explainable way."""
    if latest_source_year is None or local_latest_year is None:
        return "reachable", None
    if local_latest_year == latest_source_year:
        return "up_to_date", True
    if local_latest_year < latest_source_year:
        return "possibly_stale", False
    return "local_ahead_of_source", None


def run_source_check(
    config: SourceCheckConfig | None = None,
    *,
    write_manifest: bool = True,
    fetcher: Callable[[str, int], SourcePageResponse] = fetch_source_page,
) -> dict[str, Any]:
    """Run one MYH source check and optionally update the local manifest."""
    config = config or build_config_from_env()
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    configured_files = [file_candidate_from_config(value, config.source_url) for value in config.configured_files]

    try:
        response = fetcher(config.source_url, config.timeout_seconds)
        discovered_files = discover_excel_files(response.body, config.source_url)
        latest_source_year = extract_latest_year(discovered_files) or extract_latest_year(configured_files)
        local_latest_year = read_local_latest_source_year(config.local_csv_path)
        status, up_to_date = determine_status(latest_source_year, local_latest_year)
        message = build_status_message(
            status=status,
            discovered_count=len(discovered_files),
            configured_count=len(configured_files),
            latest_source_year=latest_source_year,
            local_latest_year=local_latest_year,
        )
        result: dict[str, Any] = {
            "checked_at": checked_at,
            "source_url": config.source_url,
            "status": status,
            "http_status": response.status_code,
            "content_type": response.content_type,
            "discovered_files": discovered_files,
            "configured_files": configured_files,
            "known_latest_source_snapshot": latest_source_year,
            "local_latest_source_year": local_latest_year,
            "up_to_date": up_to_date,
            "message": message,
            "error": None,
        }
    except Exception as exc:
        result = {
            "checked_at": checked_at,
            "source_url": config.source_url,
            "status": "error",
            "http_status": None,
            "content_type": None,
            "discovered_files": [],
            "configured_files": configured_files,
            "known_latest_source_snapshot": extract_latest_year(configured_files),
            "local_latest_source_year": read_local_latest_source_year(config.local_csv_path),
            "up_to_date": None,
            "message": "Source check could not complete. No application data was changed.",
            "error": str(exc),
        }

    if write_manifest:
        write_source_status_manifest(result, config.manifest_path)
    return result


def write_source_status_manifest(payload: dict[str, Any], manifest_path: Path = DEFAULT_MANIFEST_PATH) -> None:
    """Write the source-check manifest as readable JSON."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_source_status_manifest(manifest_path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    """Read the last source-check manifest, or return an explicit not-checked payload."""
    if not manifest_path.exists():
        return {
            "checked_at": None,
            "source_url": build_config_from_env().source_url,
            "status": "not_checked",
            "http_status": None,
            "content_type": None,
            "discovered_files": [],
            "configured_files": [],
            "known_latest_source_snapshot": None,
            "local_latest_source_year": None,
            "up_to_date": None,
            "message": "No source check has been recorded yet. Run POST /admin/source-monitor/check with an admin bearer token, or use the legacy check_source_status.py script.",
            "error": None,
        }

    return json.loads(manifest_path.read_text(encoding="utf-8"))


def build_refresh_source_metadata(manifest: dict[str, Any]) -> dict[str, str | int | None | bool]:
    """Return the source-check fields added to the refresh response."""
    return {
        "refresh_mode": "curated_csv",
        "source_check_status": manifest.get("status"),
        "source_check_checked_at": manifest.get("checked_at"),
        "source_check_message": manifest.get("message"),
        "known_latest_source_snapshot": manifest.get("known_latest_source_snapshot"),
        "local_latest_source_year": manifest.get("local_latest_source_year"),
        "source_up_to_date": manifest.get("up_to_date"),
    }

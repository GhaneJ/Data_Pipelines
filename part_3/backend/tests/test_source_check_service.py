"""Tests for the scheduler-ready MYH source-check service."""

from __future__ import annotations

import csv
from pathlib import Path

from backend.app.services import source_check


def write_small_curated_csv(path: Path, years: list[int]) -> None:
    """Write the minimum CSV shape needed by the source-year reader."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["source_year", "diarienummer"])
        writer.writeheader()
        for index, year in enumerate(years, start=1):
            writer.writerow({"source_year": year, "diarienummer": f"MYH {year}/{index}"})


def test_parse_configured_files_ignores_empty_parts() -> None:
    """Configured file lists should be forgiving about spaces and empty values."""
    parsed = source_check.parse_configured_files(" 2024.xlsx, ,https://example.test/2025.xlsx ")

    assert parsed == ("2024.xlsx", "https://example.test/2025.xlsx")


def test_discover_excel_files_from_html() -> None:
    """The source checker should discover Excel links without complex scraping."""
    html = """
    <a href="/download/resultat-2024.xlsx">2024</a>
    <a href="https://example.test/files/resultat-2025.xlsm?download=1">2025</a>
    <a href="/download/resultat-2024.xlsx">duplicate</a>
    """

    files = source_check.discover_excel_files(html, "https://www.myh.se/source/page")

    assert files == [
        {
            "file_name": "resultat-2024.xlsx",
            "url": "https://www.myh.se/download/resultat-2024.xlsx",
        },
        {
            "file_name": "resultat-2025.xlsm",
            "url": "https://example.test/files/resultat-2025.xlsm?download=1",
        },
    ]
    assert source_check.extract_latest_year(files) == 2025


def test_manifest_round_trip(tmp_path: Path) -> None:
    """The local JSON manifest should be readable after writing."""
    manifest_path = tmp_path / "source_status.json"
    payload = {
        "checked_at": "2026-05-27T10:00:00+00:00",
        "source_url": "https://example.test",
        "status": "up_to_date",
        "http_status": 200,
        "content_type": "text/html",
        "discovered_files": [],
        "configured_files": [],
        "known_latest_source_snapshot": 2025,
        "local_latest_source_year": 2025,
        "up_to_date": True,
        "message": "OK",
        "error": None,
    }

    source_check.write_source_status_manifest(payload, manifest_path)

    assert source_check.read_source_status_manifest(manifest_path) == payload


def test_read_missing_manifest_returns_not_checked(tmp_path: Path) -> None:
    """A missing manifest should be explicit instead of failing."""
    payload = source_check.read_source_status_manifest(tmp_path / "missing.json")

    assert payload["status"] == "not_checked"
    assert payload["checked_at"] is None


def test_run_source_check_reports_up_to_date_with_mocked_response(tmp_path: Path) -> None:
    """A mocked page and local CSV should produce an up-to-date result without internet."""
    csv_path = tmp_path / "curated.csv"
    manifest_path = tmp_path / "source_status.json"
    write_small_curated_csv(csv_path, [2024, 2025])

    def fake_fetcher(url: str, timeout_seconds: int) -> source_check.SourcePageResponse:
        assert url == "https://example.test/source"
        assert timeout_seconds == 3
        return source_check.SourcePageResponse(
            status_code=200,
            body='<a href="/files/myh-resultat-2025.xlsx">latest</a>',
            content_type="text/html; charset=utf-8",
        )

    result = source_check.run_source_check(
        source_check.SourceCheckConfig(
            source_url="https://example.test/source",
            manifest_path=manifest_path,
            local_csv_path=csv_path,
            timeout_seconds=3,
        ),
        fetcher=fake_fetcher,
    )

    assert result["status"] == "up_to_date"
    assert result["known_latest_source_snapshot"] == 2025
    assert result["local_latest_source_year"] == 2025
    assert result["up_to_date"] is True
    assert manifest_path.exists()


def test_run_source_check_reports_possible_staleness_with_mocked_response(tmp_path: Path) -> None:
    """A newer visible source year should be reported without changing application data."""
    csv_path = tmp_path / "curated.csv"
    write_small_curated_csv(csv_path, [2024, 2025])

    def fake_fetcher(url: str, timeout_seconds: int) -> source_check.SourcePageResponse:
        return source_check.SourcePageResponse(
            status_code=200,
            body='<a href="/files/myh-resultat-2026.xlsx">latest</a>',
        )

    result = source_check.run_source_check(
        source_check.SourceCheckConfig(
            source_url="https://example.test/source",
            manifest_path=tmp_path / "manifest.json",
            local_csv_path=csv_path,
        ),
        fetcher=fake_fetcher,
    )

    assert result["status"] == "possibly_stale"
    assert result["up_to_date"] is False
    assert "No application data was changed" not in result["message"]


def test_run_source_check_records_fetch_error(tmp_path: Path) -> None:
    """Fetch failures should become manifest-ready error payloads."""
    csv_path = tmp_path / "curated.csv"
    write_small_curated_csv(csv_path, [2025])

    def fake_fetcher(url: str, timeout_seconds: int) -> source_check.SourcePageResponse:
        raise TimeoutError("network timeout")

    result = source_check.run_source_check(
        source_check.SourceCheckConfig(
            source_url="https://example.test/source",
            manifest_path=tmp_path / "manifest.json",
            local_csv_path=csv_path,
            configured_files=("resultat-2025.xlsx",),
        ),
        fetcher=fake_fetcher,
    )

    assert result["status"] == "error"
    assert result["known_latest_source_snapshot"] == 2025
    assert result["local_latest_source_year"] == 2025
    assert "network timeout" in result["error"]

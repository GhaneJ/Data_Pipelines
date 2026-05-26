"""Tests for the manual source-check script helpers."""

from __future__ import annotations

from pathlib import Path

from backend.scripts.check_source_status import format_status_summary


def test_format_status_summary_includes_scheduler_relevant_fields(tmp_path: Path) -> None:
    """The script output should be useful for manual runs and later schedulers."""
    result = {
        "checked_at": "2026-05-27T10:00:00+00:00",
        "source_url": "https://example.test/source",
        "status": "up_to_date",
        "http_status": 200,
        "known_latest_source_snapshot": 2025,
        "local_latest_source_year": 2025,
        "up_to_date": True,
        "discovered_files": [{"file_name": "resultat-2025.xlsx", "url": "https://example.test/resultat-2025.xlsx"}],
        "configured_files": [],
        "message": "OK",
        "error": None,
    }

    summary = format_status_summary(result, tmp_path / "source_status.json")

    assert "Status: up_to_date" in summary
    assert "Latest visible source year: 2025" in summary
    assert "Manifest:" in summary

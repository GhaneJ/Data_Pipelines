"""Focused schema and CSV serialization tests."""

from __future__ import annotations

import csv
import io

from backend.app.schemas import DatabaseHealth, HealthStatus, RefreshResult
from backend.app.services.export import rows_to_csv


def test_health_schema_serialization() -> None:
    """Health response models should serialize the documented JSON shape."""
    lightweight = HealthStatus(status="ok")
    assert lightweight.model_dump() == {"status": "ok"}

    db_health = DatabaseHealth(
        status="ready",
        database_connected=True,
        required_tables={"ok": True, "checked": ["applications"], "missing": []},
        applications={"table": "applications", "ok": True, "row_count": 7641},
        lookup_tables=[{"table": "providers", "ok": True, "row_count": 100}],
    )
    assert db_health.model_dump()["applications"]["row_count"] == 7641


def test_refresh_result_schema() -> None:
    """The refresh endpoint should keep its simple summary response shape."""
    result = RefreshResult(
        status="success",
        rows_loaded=7641,
        source_file="part_2/data/processed/myh_curated_applications_2020_2025.csv",
        refreshed_at="2026-05-24T14:30:00+00:00",
    )

    assert result.status == "success"
    assert result.rows_loaded == 7641


def test_rows_to_csv_uses_stable_export_columns() -> None:
    """CSV export should include the stable header even for a small result set."""
    csv_text = rows_to_csv(
        [
            {
                "diarienummer": "MYH 2024/1",
                "source_year": 2024,
                "utbildningsnamn": "Data Engineer",
                "utbildningsomrade": "Data/IT",
                "beslut": "Beviljad",
                "beslut_normalized": "approved",
                "is_approved": True,
                "lan": "Stockholms län",
                "kommun": "Stockholm",
                "yh_poang": 400,
                "studieform": "Distans",
                "studietakt_procent": 100,
                "utbildningsanordnare": "Example Provider",
                "huvudmannatyp": "Privat",
                "huvudmannatyp_normalized": "private",
                "sokta_utbildningsomgangar": 1,
                "beviljade_utbildningsomgangar": 1,
                "sokta_platser_totalt": 30,
                "beviljade_platser_totalt": 30,
                "ignored_extra_field": "not exported",
            }
        ]
    )

    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert rows[0]["diarienummer"] == "MYH 2024/1"
    assert "ignored_extra_field" not in rows[0]
    assert "beviljade_platser_totalt" in rows[0]

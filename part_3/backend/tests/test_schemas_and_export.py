"""Focused schema and CSV serialization tests."""

from __future__ import annotations

import csv
import io

from backend.app.schemas import (
    ApplicationNote,
    ApplicationNoteCreate,
    ApplicationNoteDeleteResult,
    ApplicationNotePatch,
    ApplicationNoteUpdate,
    DatabaseHealth,
    HealthStatus,
    RefreshResult,
    SourceCheckResult,
)
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

    with_source_metadata = RefreshResult(
        status="success",
        rows_loaded=7641,
        source_file="part_2/data/processed/myh_curated_applications_2020_2025.csv",
        refreshed_at="2026-05-24T14:30:00+00:00",
        refresh_mode="curated_csv",
        source_check_status="up_to_date",
        source_up_to_date=True,
    )
    assert with_source_metadata.source_check_status == "up_to_date"


def test_source_check_result_schema() -> None:
    """Source-check responses should serialize the documented JSON shape."""
    result = SourceCheckResult(
        checked_at="2026-05-27T10:00:00+00:00",
        source_url="https://example.test",
        status="up_to_date",
        http_status=200,
        content_type="text/html",
        discovered_files=[{"file_name": "resultat-2025.xlsx", "url": "https://example.test/resultat-2025.xlsx"}],
        configured_files=[],
        known_latest_source_snapshot=2025,
        local_latest_source_year=2025,
        up_to_date=True,
        message="OK",
        error=None,
    )

    assert result.discovered_files[0].file_name == "resultat-2025.xlsx"
    assert result.up_to_date is True


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


def test_application_note_schemas() -> None:
    """Admin-note schemas should keep the protected write payload simple."""
    create_payload = ApplicationNoteCreate(note_text="Check before demo.")
    update_payload = ApplicationNoteUpdate(note_text="Replace note before demo.")
    patch_payload = ApplicationNotePatch(note_text="Patch note before demo.")
    empty_patch_payload = ApplicationNotePatch()
    note = ApplicationNote(
        id=1,
        diarienummer="MYH 2024/1",
        note_text=create_payload.note_text,
        created_at="2026-05-27T10:00:00+00:00",
        updated_at="2026-05-27T10:00:00+00:00",
    )
    delete_result = ApplicationNoteDeleteResult(note_id=note.id, deleted=True)

    assert note.diarienummer == "MYH 2024/1"
    assert update_payload.note_text == "Replace note before demo."
    assert patch_payload.note_text == "Patch note before demo."
    assert empty_patch_payload.note_text is None
    assert delete_result.model_dump() == {"note_id": 1, "deleted": True}

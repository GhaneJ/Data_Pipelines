"""Focused tests for the 3.20 MYH source-monitor service."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from backend.app.source_monitor import service
from backend.app.source_monitor.scheduler import start_scheduler_if_enabled


def test_parser_finds_official_downloads_and_ignores_pdfs() -> None:
    html = """
    <a href="/download/resultat-program-2026.xlsx">Resultat för program 2026</a>
    <a href="/download/readme.pdf">PDF instructions</a>
    <a href="https://example.test/files/resultat-2025.xlsm?download=1">2025 workbook</a>
    """

    files = service.parse_source_page(html, "https://www.myh.se/source/page")

    assert [file.file_name for file in files] == ["resultat-program-2026.xlsx", "resultat-2025.xlsm"]
    assert files[0].source_year == 2026
    assert files[1].file_url == "https://example.test/files/resultat-2025.xlsm?download=1"


def test_extract_source_year_returns_latest_visible_year() -> None:
    assert service.extract_source_year("resultat-2024.xlsx", "archive/resultat-2026.xlsx") == 2026
    assert service.extract_source_year("no-year.xlsx") is None


def write_tiny_official_workbook(path: Path, duplicate: bool = False) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tabell 3"
    sheet.append([
        "Diarienummer",
        "Utbildningsnamn",
        "Utbildningsområde",
        "Beslut",
        "Län",
        "Kommun",
        "YH-poäng",
        "Studieform",
        "Utbildningsanordnare",
        "Huvudmannatyp",
    ])
    sheet.append([
        "MYH 2026/1",
        "Cloud Data Engineer",
        "Data/IT",
        "Beviljad",
        "Stockholms län",
        "Stockholm",
        400,
        "Distans",
        "Example Provider",
        "Privat",
    ])
    sheet.append([
        "MYH 2026/1" if duplicate else "MYH 2026/2",
        "Industrial AI Specialist",
        "Data/IT",
        "Avslag",
        "Västra Götalands län",
        "Göteborg",
        300,
        "Bunden",
        "Example Provider 2",
        "Kommun",
    ])
    workbook.save(path)


def test_transform_official_excel_file_uses_tabell_3_rules(tmp_path) -> None:
    source_path = tmp_path / "resultat-program-2026.xlsx"
    write_tiny_official_workbook(source_path)

    rows = service.transform_official_source_file(source_path, source_year=2026, source_file_name=source_path.name)

    assert len(rows) == 2
    assert rows[0]["source_year"] == "2026"
    assert rows[0]["source_sheet"] == "Tabell 3"
    assert rows[0]["beslut_normalized"] == "approved"
    assert rows[0]["is_distance_based"] == "true"
    assert rows[1]["beslut_normalized"] == "rejected"
    assert rows[1]["huvudmannatyp_normalized"] == "municipal"


def test_transform_rejects_duplicate_diarienummer(tmp_path) -> None:
    source_path = tmp_path / "resultat-program-2026.xlsx"
    write_tiny_official_workbook(source_path, duplicate=True)

    with pytest.raises(ValueError, match="diarienummer is not unique"):
        service.transform_official_source_file(source_path, source_year=2026, source_file_name=source_path.name)


def test_scheduler_is_disabled_by_default() -> None:
    config = service.SourceMonitorConfig(monitor_enabled=False)

    assert start_scheduler_if_enabled(config) is None

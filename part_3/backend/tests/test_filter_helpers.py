"""Focused tests for filter and guardrail helpers."""

from __future__ import annotations

import pytest

from backend.app.services.common import (
    ApplicationFilters,
    build_application_filter_clause,
    resolve_export_source_year,
    validate_year_range,
)
from backend.app.services.providers import build_provider_filter_clause


def test_application_filter_clause_uses_parameters_not_inline_values() -> None:
    """Text filters should become SQL parameters, not string-concatenated values."""
    where_sql, params = build_application_filter_clause(
        ApplicationFilters(source_year=2024, decision="approved", region="Stockholm", provider="KYH")
    )

    assert "a.source_year = %(source_year)s" in where_sql
    assert "a.decision_code = %(decision)s" in where_sql
    assert "l.lan ILIKE %(region)s" in where_sql
    assert "p.utbildningsanordnare ILIKE %(provider)s" in where_sql
    assert "Stockholm" not in where_sql
    assert "KYH" not in where_sql
    assert params == {
        "source_year": 2024,
        "decision": "approved",
        "region": "%Stockholm%",
        "provider": "%KYH%",
    }


def test_export_year_alias_guardrail_accepts_matching_values() -> None:
    """The export endpoint may receive year or source_year, but they must agree."""
    assert resolve_export_source_year(year=2024, source_year=None) == 2024
    assert resolve_export_source_year(year=None, source_year=2024) == 2024
    assert resolve_export_source_year(year=2024, source_year=2024) == 2024


def test_export_year_alias_guardrail_rejects_conflict() -> None:
    """Conflicting year aliases should be rejected before building SQL."""
    with pytest.raises(ValueError, match="Use either year or source_year"):
        resolve_export_source_year(year=2024, source_year=2025)


def test_trend_year_range_guardrail() -> None:
    """Trend helpers should reject an impossible range."""
    validate_year_range(2020, 2025)

    with pytest.raises(ValueError, match="year_from"):
        validate_year_range(2025, 2020)


def test_provider_filter_clause_uses_parameterized_search() -> None:
    """Provider search should use an ILIKE parameter."""
    where_sql, params = build_provider_filter_clause("Folkuniversitetet")

    assert where_sql == "WHERE p.utbildningsanordnare ILIKE %(search)s"
    assert "Folkuniversitetet" not in where_sql
    assert params == {"search": "%Folkuniversitetet%"}

"""Compatibility exports for the backend service layer.

New code should import from ``backend.app.services``. This module keeps older
script or test imports working while the backend is organized into routers and
services.
"""

from __future__ import annotations

from backend.app.services.applications import fetch_application_by_diarienummer, fetch_applications
from backend.app.services.common import (
    APPLICATION_COUNT_SQL,
    APPLICATION_SELECT_SQL,
    ApplicationFilters,
    TrendFilters,
    build_application_filter_clause,
    like_pattern,
    resolve_export_source_year,
    validate_year_range,
)
from backend.app.services.export import (
    EXPORT_APPLICATION_COLUMNS,
    EXPORT_APPLICATION_SELECT_SQL,
    fetch_export_applications,
    rows_to_csv,
)
from backend.app.services.providers import (
    PROVIDER_SUMMARY_SELECT_SQL,
    build_provider_filter_clause,
    fetch_provider_applications,
    fetch_provider_by_id,
    fetch_providers,
)
from backend.app.services.stats import (
    build_decision_trend_filter_clause,
    build_education_area_trend_filter_clause,
    build_region_trend_filter_clause,
    fetch_stats_by_decision,
    fetch_stats_by_education_area,
    fetch_stats_by_region,
    fetch_stats_by_year,
    fetch_trend_by_decision,
    fetch_trend_by_education_area,
    fetch_trend_by_region,
)

_like_pattern = like_pattern

__all__ = [
    "APPLICATION_COUNT_SQL",
    "APPLICATION_SELECT_SQL",
    "EXPORT_APPLICATION_COLUMNS",
    "EXPORT_APPLICATION_SELECT_SQL",
    "PROVIDER_SUMMARY_SELECT_SQL",
    "ApplicationFilters",
    "TrendFilters",
    "_like_pattern",
    "build_application_filter_clause",
    "build_decision_trend_filter_clause",
    "build_education_area_trend_filter_clause",
    "build_provider_filter_clause",
    "build_region_trend_filter_clause",
    "fetch_application_by_diarienummer",
    "fetch_applications",
    "fetch_export_applications",
    "fetch_provider_applications",
    "fetch_provider_by_id",
    "fetch_providers",
    "fetch_stats_by_decision",
    "fetch_stats_by_education_area",
    "fetch_stats_by_region",
    "fetch_stats_by_year",
    "fetch_trend_by_decision",
    "fetch_trend_by_education_area",
    "fetch_trend_by_region",
    "resolve_export_source_year",
    "rows_to_csv",
    "validate_year_range",
]

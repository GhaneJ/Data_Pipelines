"""Pydantic response models for the MYH applications API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class Application(BaseModel):
    """One curated MYH application returned by the API."""

    diarienummer: str
    source_year: int
    source_file: str
    source_sheet: str
    source_row: int
    utbildningsnamn: str
    utbildningsomrade: str
    beslut: str
    beslut_normalized: str
    is_approved: bool
    lan: str
    kommun: str
    flera_kommuner: str
    has_multiple_municipalities: bool
    antal_kommuner: int
    yh_poang: int
    studieform: str
    is_distance_based: bool
    studietakt_procent: int
    examenstyp: str | None = None
    utbildningsanordnare: str
    huvudmannatyp: str
    huvudmannatyp_normalized: str
    sokta_utbildningsomgangar: int
    beviljade_utbildningsomgangar: int
    sun5_inriktning: str | None = None
    sun5_inriktning_namn: str | None = None
    seqf_niva: Decimal | None = None
    smalt_yrkesomrade: str | None = None
    sokta_platser_per_utbildningsomgang: Decimal | None = None
    sokta_platser_totalt: Decimal | None = None
    beviljade_platser_totalt: Decimal | None = None


class ApplicationList(BaseModel):
    """Paginated application list response."""

    total: int
    limit: int
    offset: int
    items: list[Application]


class YearStats(BaseModel):
    """Application statistics grouped by source year."""

    source_year: int
    total_applications: int
    approved_applications: int
    rejected_applications: int
    withdrawn_applications: int
    approval_rate_percent: float


class RegionStats(BaseModel):
    """Application statistics grouped by län/region."""

    lan: str
    total_applications: int
    approved_applications: int
    rejected_applications: int
    withdrawn_applications: int
    approval_rate_percent: float


class EducationAreaStats(BaseModel):
    """Application statistics grouped by education area."""

    education_area_id: int
    utbildningsomrade: str
    total_applications: int
    approved_applications: int
    rejected_applications: int
    withdrawn_applications: int
    approval_rate_percent: float


class DecisionStats(BaseModel):
    """Application statistics grouped by normalized decision."""

    decision_code: str
    decision_label: str
    total_applications: int
    application_share_percent: float


class DecisionTrend(BaseModel):
    """Yearly application count for one normalized decision."""

    source_year: int
    decision_code: str
    decision_label: str
    application_count: int


class RegionTrend(BaseModel):
    """Yearly application count for one län/region."""

    source_year: int
    lan: str
    application_count: int


class EducationAreaTrend(BaseModel):
    """Yearly application count for one education area."""

    source_year: int
    education_area_id: int
    utbildningsomrade: str
    application_count: int


class ProviderSummary(BaseModel):
    """Provider row returned by the provider browsing endpoint."""

    provider_id: int
    utbildningsanordnare: str
    total_applications: int
    approved_applications: int
    first_year: int | None = None
    last_year: int | None = None


class ProviderList(BaseModel):
    """Paginated provider list response."""

    total: int
    limit: int
    offset: int
    items: list[ProviderSummary]


class RefreshResult(BaseModel):
    """Summary returned after reloading the database from the curated CSV."""

    status: str
    rows_loaded: int
    source_file: str
    refreshed_at: str

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

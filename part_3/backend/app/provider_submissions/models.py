"""Models for provider-created application submissions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_TEXT_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 4000


class ProviderSubmissionStatus(str, Enum):
    """Statuses owned by the 3.17 provider submission workflow."""

    DRAFT = "draft"
    SUBMITTED = "submitted"


class ProviderSubmissionIdentity(BaseModel):
    """Resolved provider identity for provider submission routes."""

    user_id: UUID
    provider_id: str
    provider_name: str | None = None


class ProviderSubmissionBase(BaseModel):
    """Shared provider submission fields."""

    target_year: int | None = Field(default=None, ge=2020, le=2100)
    education_name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    education_area: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    municipality: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    region: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    yh_points: int | None = Field(default=None, gt=0, le=5000)
    study_form: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    study_pace_percent: int | None = Field(default=None, ge=1, le=100)
    head_provider_type: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    notes: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "education_name",
        "education_area",
        "municipality",
        "region",
        "study_form",
        "head_provider_type",
        "description",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_text_fields(cls, value: object) -> object:
        """Trim text values before field-level validation."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "education_area",
        "municipality",
        "region",
        "study_form",
        "head_provider_type",
        "description",
        "notes",
    )
    @classmethod
    def blank_optional_text_becomes_none(cls, value: str | None) -> str | None:
        """Store blank optional text values as NULL instead of empty strings."""
        if value == "":
            return None
        return value


class ProviderSubmissionCreateRequest(ProviderSubmissionBase):
    """Payload for creating a draft provider application submission."""


class ProviderSubmissionUpdateRequest(BaseModel):
    """Payload for updating editable draft provider submission fields.

    The model intentionally has no status, provider_id, provider_name,
    created_by_user_id, submitted_at, or timestamp fields, and forbids extra
    values so callers cannot tamper with ownership or workflow state.
    """

    target_year: int | None = Field(default=None, ge=2020, le=2100)
    education_name: str | None = Field(default=None, min_length=1, max_length=MAX_TEXT_LENGTH)
    education_area: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    municipality: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    region: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    yh_points: int | None = Field(default=None, gt=0, le=5000)
    study_form: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    study_pace_percent: int | None = Field(default=None, ge=1, le=100)
    head_provider_type: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    notes: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "education_name",
        "education_area",
        "municipality",
        "region",
        "study_form",
        "head_provider_type",
        "description",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_text_fields(cls, value: object) -> object:
        """Trim text values before field-level validation."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "education_area",
        "municipality",
        "region",
        "study_form",
        "head_provider_type",
        "description",
        "notes",
    )
    @classmethod
    def blank_optional_text_becomes_none(cls, value: str | None) -> str | None:
        """Store blank optional text values as NULL instead of empty strings."""
        if value == "":
            return None
        return value


class ProviderSubmissionResponse(BaseModel):
    """Provider submission response returned by CRUD endpoints."""

    id: UUID
    provider_id: str
    provider_name: str | None = None
    created_by_user_id: UUID
    status: ProviderSubmissionStatus
    target_year: int | None = None
    education_name: str
    education_area: str | None = None
    municipality: str | None = None
    region: str | None = None
    yh_points: int | None = None
    study_form: str | None = None
    study_pace_percent: int | None = None
    head_provider_type: str | None = None
    description: str | None = None
    notes: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProviderSubmissionListResponse(BaseModel):
    """Paginated list response for provider-owned submissions."""

    items: list[ProviderSubmissionResponse]
    limit: int
    offset: int

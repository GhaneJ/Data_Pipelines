"""Models for admin review of provider-created application submissions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.provider_submissions.models import MAX_DESCRIPTION_LENGTH, ProviderSubmissionStatus


class ReviewEventAction(str, Enum):
    """Audit event names for provider-submission workflow transitions."""

    SUBMITTED = "submitted"
    REVIEW_STARTED = "review_started"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUBMITTED = "resubmitted"


class ReviewActorRole(str, Enum):
    """Actor roles stored in review history events."""

    ADMIN = "admin"
    PROVIDER = "provider"
    SYSTEM = "system"


class AdminReviewRequest(BaseModel):
    """Request body shared by admin review transition endpoints."""

    review_notes: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator("review_notes", mode="before")
    @classmethod
    def strip_review_notes(cls, value: object) -> object:
        """Trim review notes before storage."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("review_notes")
    @classmethod
    def blank_notes_become_none(cls, value: str | None) -> str | None:
        """Store blank notes as NULL rather than empty strings."""
        if value == "":
            return None
        return value


class AdminProviderSubmissionResponse(BaseModel):
    """Admin-visible provider submission detail with review metadata."""

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
    review_started_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminProviderSubmissionListResponse(BaseModel):
    """Paginated admin review queue response."""

    items: list[AdminProviderSubmissionResponse]
    limit: int
    offset: int


class ReviewEventResponse(BaseModel):
    """Review/status-transition event returned to admins."""

    id: UUID
    submission_id: UUID
    actor_user_id: UUID | None = None
    actor_role: ReviewActorRole
    action: ReviewEventAction
    from_status: ProviderSubmissionStatus | None = None
    to_status: ProviderSubmissionStatus
    notes: str | None = None
    created_at: datetime

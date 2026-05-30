"""Repository tests for provider application submissions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.auth.models import Role
from backend.app.provider_submissions.models import (
    ProviderSubmissionCreateRequest,
    ProviderSubmissionIdentity,
    ProviderSubmissionStatus,
    ProviderSubmissionUpdateRequest,
)
from backend.app.provider_submissions.repositories import (
    EmptyProviderSubmissionUpdateError,
    ProviderSubmissionStateError,
    create_provider_submission,
    delete_provider_submission,
    get_provider_name,
    get_provider_submission,
    list_provider_submissions,
    submit_provider_submission,
    update_provider_submission,
)
from backend.tests.auth_test_utils import FakeAuthConnection


def provider_identity(conn: FakeAuthConnection, provider_id: str = "999999") -> ProviderSubmissionIdentity:
    user = conn.add_user(username=f"provider-{provider_id}", password="provider-password", role=Role.PROVIDER, provider_id=provider_id)
    return ProviderSubmissionIdentity(user_id=user["id"], provider_id=provider_id, provider_name=f"Provider {provider_id}")


def create_payload(**overrides: object) -> ProviderSubmissionCreateRequest:
    data = {
        "target_year": 2026,
        "education_name": "  Cloud Data Engineer  ",
        "education_area": "Data/IT",
        "municipality": "Stockholm",
        "region": "Stockholms län",
        "yh_points": 400,
        "study_form": "Distans",
        "study_pace_percent": 100,
        "head_provider_type": "Privat",
        "description": "Provider-created draft application for future review.",
        "notes": "Initial local validation draft.",
    }
    data.update(overrides)
    return ProviderSubmissionCreateRequest(**data)


def test_provider_name_resolves_from_curated_provider_table_when_available() -> None:
    conn = FakeAuthConnection()
    conn.add_provider_name("999999", "Curated Provider Name")

    assert get_provider_name(conn, "999999") == "Curated Provider Name"
    assert get_provider_name(conn, "not-numeric") is None


def test_provider_can_create_draft_submission_with_ownership() -> None:
    conn = FakeAuthConnection()
    identity = provider_identity(conn)

    row = create_provider_submission(conn, identity=identity, payload=create_payload())

    assert row["status"] == "draft"
    assert row["provider_id"] == "999999"
    assert row["provider_name"] == "Provider 999999"
    assert row["created_by_user_id"] == str(identity.user_id)
    assert row["education_name"] == "Cloud Data Engineer"
    assert conn.provider_submissions_by_id[row["id"]]["provider_id"] == "999999"


def test_provider_can_list_only_own_submissions_with_filters() -> None:
    conn = FakeAuthConnection()
    own = conn.add_provider_submission(provider_id="999999", status="draft", target_year=2026)
    conn.add_provider_submission(provider_id="999999", status="submitted", target_year=2025)
    conn.add_provider_submission(provider_id="888888", status="draft", target_year=2026)

    rows = list_provider_submissions(conn, provider_id="999999")
    draft_rows = list_provider_submissions(conn, provider_id="999999", status=ProviderSubmissionStatus.DRAFT, target_year=2026)

    assert {row["provider_id"] for row in rows} == {"999999"}
    assert {row["id"] for row in draft_rows} == {own["id"]}


def test_provider_can_read_own_submission_and_other_provider_is_not_found() -> None:
    conn = FakeAuthConnection()
    own = conn.add_provider_submission(provider_id="999999")
    other = conn.add_provider_submission(provider_id="888888")

    assert get_provider_submission(conn, provider_id="999999", submission_id=own["id"])["id"] == own["id"]
    assert get_provider_submission(conn, provider_id="999999", submission_id=other["id"]) is None
    assert get_provider_submission(conn, provider_id="999999", submission_id="00000000-0000-0000-0000-000000000000") is None


def test_provider_can_update_own_draft_but_not_submitted_submission() -> None:
    conn = FakeAuthConnection()
    draft = conn.add_provider_submission(provider_id="999999", status="draft")
    submitted = conn.add_provider_submission(provider_id="999999", status="submitted")

    updated = update_provider_submission(
        conn,
        provider_id="999999",
        submission_id=draft["id"],
        payload=ProviderSubmissionUpdateRequest(notes="Updated note", study_pace_percent=75),
    )

    assert updated is not None
    assert updated["notes"] == "Updated note"
    assert updated["study_pace_percent"] == 75
    assert updated["status"] == "draft"
    with pytest.raises(ProviderSubmissionStateError):
        update_provider_submission(
            conn,
            provider_id="999999",
            submission_id=submitted["id"],
            payload=ProviderSubmissionUpdateRequest(notes="Should fail"),
        )


def test_update_rejects_empty_payload_and_direct_status_tampering() -> None:
    conn = FakeAuthConnection()
    draft = conn.add_provider_submission(provider_id="999999")

    with pytest.raises(EmptyProviderSubmissionUpdateError):
        update_provider_submission(
            conn,
            provider_id="999999",
            submission_id=draft["id"],
            payload=ProviderSubmissionUpdateRequest(),
        )

    with pytest.raises(ValidationError):
        ProviderSubmissionUpdateRequest(status="submitted")


def test_provider_can_delete_draft_but_not_submitted_submission() -> None:
    conn = FakeAuthConnection()
    draft = conn.add_provider_submission(provider_id="999999", status="draft")
    submitted = conn.add_provider_submission(provider_id="999999", status="submitted")

    assert delete_provider_submission(conn, provider_id="999999", submission_id=draft["id"]) is True
    assert draft["id"] not in conn.provider_submissions_by_id
    assert delete_provider_submission(conn, provider_id="999999", submission_id="00000000-0000-0000-0000-000000000000") is None
    with pytest.raises(ProviderSubmissionStateError):
        delete_provider_submission(conn, provider_id="999999", submission_id=submitted["id"])


def test_provider_can_submit_own_draft_and_submitted_at_is_set() -> None:
    conn = FakeAuthConnection()
    draft = conn.add_provider_submission(provider_id="999999", status="draft")

    submitted = submit_provider_submission(conn, provider_id="999999", submission_id=draft["id"])

    assert submitted is not None
    assert submitted["status"] == "submitted"
    assert submitted["submitted_at"] is not None
    with pytest.raises(ProviderSubmissionStateError):
        submit_provider_submission(conn, provider_id="999999", submission_id=draft["id"])


def test_request_model_validation_rejects_bad_values() -> None:
    with pytest.raises(ValidationError):
        create_payload(education_name="   ")
    with pytest.raises(ValidationError):
        create_payload(study_pace_percent=101)
    with pytest.raises(ValidationError):
        create_payload(yh_points=0)

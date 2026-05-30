"""Repository tests for admin provider-submission review workflow."""

from __future__ import annotations

import pytest

from backend.app.admin_reviews.models import AdminReviewRequest, ReviewActorRole, ReviewEventAction
from backend.app.admin_reviews.repositories import (
    approve_submission,
    get_admin_provider_submission,
    list_admin_provider_submissions,
    list_review_events,
    reject_submission,
    request_changes,
    start_review,
)
from backend.app.auth.models import Role
from backend.app.provider_submissions.models import ProviderSubmissionUpdateRequest
from backend.app.provider_submissions.repositories import (
    ProviderSubmissionStateError,
    create_review_event,
    delete_provider_submission,
    submit_provider_submission,
    update_provider_submission,
)
from backend.tests.auth_test_utils import FakeAuthConnection


def admin_user(conn: FakeAuthConnection) -> dict:
    return conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)


def provider_user(conn: FakeAuthConnection, provider_id: str = "999999") -> dict:
    return conn.add_user(username=f"provider-{provider_id}", password="provider-password", role=Role.PROVIDER, provider_id=provider_id)


def test_admin_can_list_and_read_submitted_provider_submissions() -> None:
    conn = FakeAuthConnection()
    provider = provider_user(conn)
    submitted = conn.add_provider_submission(provider_id="999999", created_by_user_id=provider["id"], status="submitted")
    conn.add_provider_submission(provider_id="999999", created_by_user_id=provider["id"], status="draft")

    rows = list_admin_provider_submissions(conn)
    detail = get_admin_provider_submission(conn, submission_id=submitted["id"])

    assert [row["id"] for row in rows] == [submitted["id"]]
    assert detail is not None
    assert detail["id"] == submitted["id"]


def test_admin_start_review_from_submitted_and_from_draft_fails() -> None:
    conn = FakeAuthConnection()
    admin = admin_user(conn)
    submitted = conn.add_provider_submission(status="submitted")
    draft = conn.add_provider_submission(status="draft")

    started = start_review(
        conn,
        submission_id=submitted["id"],
        admin_user_id=admin["id"],
        payload=AdminReviewRequest(review_notes="Initial admin review started."),
    )

    assert started is not None
    assert started["status"] == "under_review"
    assert started["review_started_at"] is not None
    assert started["reviewed_by_user_id"] == admin["id"]
    assert len(conn.review_events_by_id) == 1
    assert next(iter(conn.review_events_by_id.values()))["action"] == "review_started"
    with pytest.raises(ProviderSubmissionStateError):
        start_review(conn, submission_id=draft["id"], admin_user_id=admin["id"], payload=AdminReviewRequest())


@pytest.mark.parametrize(
    ("action", "expected_status", "expected_event"),
    [
        (request_changes, "needs_changes", "changes_requested"),
        (approve_submission, "approved", "approved"),
        (reject_submission, "rejected", "rejected"),
    ],
)
def test_admin_review_decisions_work_from_submitted_and_draft_fails(action, expected_status: str, expected_event: str) -> None:
    conn = FakeAuthConnection()
    admin = admin_user(conn)
    submitted = conn.add_provider_submission(status="submitted")
    draft = conn.add_provider_submission(status="draft")

    row = action(
        conn,
        submission_id=submitted["id"],
        admin_user_id=admin["id"],
        payload=AdminReviewRequest(review_notes="Reviewed."),
    )

    assert row is not None
    assert row["status"] == expected_status
    assert row["reviewed_by_user_id"] == admin["id"]
    assert row["reviewed_at"] is not None
    assert row["review_notes"] == "Reviewed."
    assert next(iter(conn.review_events_by_id.values()))["action"] == expected_event
    with pytest.raises(ProviderSubmissionStateError):
        action(conn, submission_id=draft["id"], admin_user_id=admin["id"], payload=AdminReviewRequest())


def test_admin_decisions_work_from_under_review() -> None:
    for action, expected_status in (
        (request_changes, "needs_changes"),
        (approve_submission, "approved"),
        (reject_submission, "rejected"),
    ):
        conn = FakeAuthConnection()
        admin = admin_user(conn)
        under_review = conn.add_provider_submission(status="under_review")

        row = action(conn, submission_id=under_review["id"], admin_user_id=admin["id"], payload=AdminReviewRequest())

        assert row is not None
        assert row["status"] == expected_status


def test_review_events_are_ordered() -> None:
    conn = FakeAuthConnection()
    submission = conn.add_provider_submission(status="submitted")

    create_review_event(
        conn,
        submission_id=submission["id"],
        actor_user_id=None,
        actor_role=ReviewActorRole.PROVIDER,
        action=ReviewEventAction.SUBMITTED,
        from_status="draft",
        to_status="submitted",
    )
    create_review_event(
        conn,
        submission_id=submission["id"],
        actor_user_id=None,
        actor_role=ReviewActorRole.ADMIN,
        action=ReviewEventAction.REVIEW_STARTED,
        from_status="submitted",
        to_status="under_review",
    )

    events = list_review_events(conn, submission_id=submission["id"])

    assert events is not None
    assert [event["action"] for event in events] == ["submitted", "review_started"]
    assert list_review_events(conn, submission_id="00000000-0000-0000-0000-000000000000") is None


def test_provider_can_update_and_resubmit_needs_changes_but_cannot_delete_it() -> None:
    conn = FakeAuthConnection()
    provider = provider_user(conn)
    needs_changes = conn.add_provider_submission(
        provider_id="999999",
        created_by_user_id=provider["id"],
        status="needs_changes",
    )

    updated = update_provider_submission(
        conn,
        provider_id="999999",
        submission_id=needs_changes["id"],
        payload=ProviderSubmissionUpdateRequest(notes="Clarified requested details."),
    )
    resubmitted = submit_provider_submission(
        conn,
        provider_id="999999",
        submission_id=needs_changes["id"],
        actor_user_id=provider["id"],
    )

    assert updated is not None
    assert updated["status"] == "needs_changes"
    assert updated["notes"] == "Clarified requested details."
    assert resubmitted is not None
    assert resubmitted["status"] == "submitted"
    assert next(iter(conn.review_events_by_id.values()))["action"] == "resubmitted"
    with pytest.raises(ProviderSubmissionStateError):
        delete_provider_submission(conn, provider_id="999999", submission_id=needs_changes["id"])


@pytest.mark.parametrize("status", ["submitted", "under_review", "approved", "rejected"])
def test_provider_cannot_update_locked_review_statuses(status: str) -> None:
    conn = FakeAuthConnection()
    row = conn.add_provider_submission(provider_id="999999", status=status)

    with pytest.raises(ProviderSubmissionStateError):
        update_provider_submission(
            conn,
            provider_id="999999",
            submission_id=row["id"],
            payload=ProviderSubmissionUpdateRequest(notes="Should fail"),
        )

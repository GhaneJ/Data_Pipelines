import { FormEvent, useEffect, useState } from "react";
import { approveSubmission, listAdminProviderSubmissions, listReviewEvents, rejectSubmission, requestChanges, startReview } from "@/api/adminReviews";
import type { ProviderSubmission, ReviewEvent, SubmissionStatus } from "@/api/types";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

const REVIEWABLE: SubmissionStatus[] = ["submitted", "under_review", "needs_changes"];

type ReviewAction = "start" | "changes" | "approve" | "reject";

function actionLabel(action: ReviewAction) {
  if (action === "start") return "Start review";
  if (action === "changes") return "Request changes";
  if (action === "approve") return "Approve";
  return "Reject";
}

function actionHelp(action: ReviewAction) {
  if (action === "start") return "Mark this submission as under review and record a workflow event.";
  if (action === "changes") return "Send feedback to the provider so they can update and resubmit.";
  if (action === "approve") return "Approve the provider submission in the workflow history.";
  return "Reject the provider submission and preserve the decision history.";
}

export function AdminReviewsPage() {
  const [items, setItems] = useState<ProviderSubmission[]>([]);
  const [selected, setSelected] = useState<ProviderSubmission | null>(null);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [statusFilter, setStatusFilter] = useState<SubmissionStatus | "">("");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [reviewAction, setReviewAction] = useState<ReviewAction>("start");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

  async function load() {
    setStatus("loading");
    setError(null);
    try {
      const result = await listAdminProviderSubmissions({ status: statusFilter || undefined, limit: 100 });
      setItems(result.items);
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => {
    void load();
  }, [statusFilter]);

  async function select(item: ProviderSubmission) {
    setSelected(item);
    setReviewAction(item.status === "submitted" ? "start" : "changes");
    setReviewNotes(item.status === "needs_changes" ? item.review_notes ?? "" : "");
    setReviewMessage(null);
    try {
      setEvents(await listReviewEvents(item.id));
    } catch {
      setEvents([]);
    }
  }

  async function transition(action: ReviewAction, notes?: string) {
    if (!selected) return;
    setError(null);
    const cleanNotes = notes?.trim() || undefined;
    let updated: ProviderSubmission;
    if (action === "start") updated = await startReview(selected.id, cleanNotes);
    else if (action === "changes") updated = await requestChanges(selected.id, cleanNotes);
    else if (action === "approve") updated = await approveSubmission(selected.id, cleanNotes);
    else updated = await rejectSubmission(selected.id, cleanNotes);
    setSelected(updated);
    setReviewMessage(`${actionLabel(action)} completed.`);
    setReviewNotes("");
    await load();
    setEvents(await listReviewEvents(updated.id));
  }

  function submitReviewAction(event: FormEvent) {
    event.preventDefault();
    void transition(reviewAction, reviewNotes);
  }

  const selectedCanReview = selected && (selected.status === "submitted" || selected.status === "under_review");

  return (
    <div className="split-grid review-workspace-grid">
      <section className="panel table-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Admin review</p>
            <h2>Provider submission queue</h2>
          </div>
          <label className="inline-filter">Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as SubmissionStatus | "")}><option value="">All</option>{REVIEWABLE.map((statusValue) => <option key={statusValue} value={statusValue}>{statusValue}</option>)}</select></label>
        </div>
        {error !== null && <ErrorPanel error={error} />}
        {status === "loading" && <LoadingState text="Loading review queue..." />}
        {status === "success" && items.length === 0 && <EmptyState title="No provider submissions" text="Submitted provider records will appear here." />}
        {status === "success" && items.length > 0 && (
          <table className="records-table review-table">
            <thead><tr><th>Education</th><th>Provider</th><th>Status</th><th>Updated</th></tr></thead>
            <tbody>{items.map((item) => <tr key={item.id} className={selected?.id === item.id ? "selected-row" : ""} onClick={() => void select(item)}><td><strong>{item.education_name}</strong><span>{item.municipality ?? "—"} · {item.region ?? "—"}</span></td><td>{item.provider_name ?? item.provider_id}</td><td><StatusBadge status={item.status} /></td><td>{new Date(item.updated_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
        )}
      </section>
      <section className="panel review-detail-panel">
        <h2>Review detail</h2>
        {!selected ? <p className="muted">Open a submitted provider record to review it.</p> : (
          <div className="detail-stack">
            <StatusBadge status={selected.status} />
            <h3>{selected.education_name}</h3>
            <p>{selected.description ?? "No description."}</p>
            <dl className="metadata"><dt>Provider</dt><dd>{selected.provider_name ?? selected.provider_id}</dd><dt>Target year</dt><dd>{selected.target_year ?? "—"}</dd><dt>Review notes</dt><dd>{selected.review_notes ?? "—"}</dd></dl>
            {reviewMessage && <div className="alert alert-success compact-alert">{reviewMessage}</div>}
            {selectedCanReview && (
              <form className="review-action-card" onSubmit={submitReviewAction}>
                <div className="section-heading compact">
                  <div>
                    <p className="eyebrow">Decision action</p>
                    <h3>Apply review decision</h3>
                  </div>
                </div>
                <label className="field">Action
                  <select value={reviewAction} onChange={(event) => setReviewAction(event.target.value as ReviewAction)}>
                    {selected.status === "submitted" && <option value="start">Start review</option>}
                    <option value="changes">Request changes</option>
                    <option value="approve">Approve</option>
                    <option value="reject">Reject</option>
                  </select>
                </label>
                <label className="field wide">Review note
                  <textarea value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder={reviewAction === "changes" ? "Write clear feedback for the provider." : "Optional decision note."} />
                </label>
                <p className="muted action-help">{actionHelp(reviewAction)}</p>
                <div className="actions action-cluster">
                  <button type="submit" className={reviewAction === "approve" || reviewAction === "start" ? "button primary" : "button secondary"}>{actionLabel(reviewAction)}</button>
                </div>
              </form>
            )}
            {selected.status === "submitted" && (
              <ConfirmButton className="button secondary" confirmText="Start review without adding a note?" title="Start review" confirmLabel="Start review" onConfirm={() => transition("start")}>Quick start review</ConfirmButton>
            )}
            <h4>Workflow history</h4>
            {events.length === 0 ? <p className="muted">No review events yet.</p> : <ul className="timeline">{events.map((event) => <li key={event.id}><strong>{event.action}</strong> · {event.from_status ?? "new"} → {event.to_status}<span>{event.notes ?? ""}</span></li>)}</ul>}
          </div>
        )}
      </section>
    </div>
  );
}

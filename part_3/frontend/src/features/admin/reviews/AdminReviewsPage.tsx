import { useEffect, useState } from "react";
import { approveSubmission, listAdminProviderSubmissions, listReviewEvents, rejectSubmission, requestChanges, startReview } from "@/api/adminReviews";
import type { ProviderSubmission, ReviewEvent, SubmissionStatus } from "@/api/types";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

const REVIEWABLE: SubmissionStatus[] = ["submitted", "under_review", "needs_changes"];

export function AdminReviewsPage() {
  const [items, setItems] = useState<ProviderSubmission[]>([]);
  const [selected, setSelected] = useState<ProviderSubmission | null>(null);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [statusFilter, setStatusFilter] = useState<SubmissionStatus | "">("");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);

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
    try {
      setEvents(await listReviewEvents(item.id));
    } catch {
      setEvents([]);
    }
  }

  async function transition(action: "start" | "changes" | "approve" | "reject") {
    if (!selected) return;
    const notes = window.prompt("Review notes", action === "changes" ? "Please update the highlighted fields." : "") ?? undefined;
    let updated: ProviderSubmission;
    if (action === "start") updated = await startReview(selected.id, notes);
    else if (action === "changes") updated = await requestChanges(selected.id, notes);
    else if (action === "approve") updated = await approveSubmission(selected.id, notes);
    else updated = await rejectSubmission(selected.id, notes);
    setSelected(updated);
    await load();
    setEvents(await listReviewEvents(updated.id));
  }

  return (
    <div className="split-grid">
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
          <table>
            <thead><tr><th>Education</th><th>Provider</th><th>Status</th><th>Updated</th></tr></thead>
            <tbody>{items.map((item) => <tr key={item.id} className={selected?.id === item.id ? "selected-row" : ""} onClick={() => void select(item)}><td><strong>{item.education_name}</strong><span>{item.municipality ?? "—"} · {item.region ?? "—"}</span></td><td>{item.provider_name ?? item.provider_id}</td><td><StatusBadge status={item.status} /></td><td>{new Date(item.updated_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
        )}
      </section>
      <section className="panel">
        <h2>Review detail</h2>
        {!selected ? <p className="muted">Open a submitted provider record to review it.</p> : (
          <div className="detail-stack">
            <StatusBadge status={selected.status} />
            <h3>{selected.education_name}</h3>
            <p>{selected.description ?? "No description."}</p>
            <dl className="metadata"><dt>Provider</dt><dd>{selected.provider_name ?? selected.provider_id}</dd><dt>Target year</dt><dd>{selected.target_year ?? "—"}</dd><dt>Review notes</dt><dd>{selected.review_notes ?? "—"}</dd></dl>
            <div className="actions">
              {selected.status === "submitted" && <ConfirmButton className="button primary" confirmText="Start review?" onConfirm={() => transition("start")}>Start review</ConfirmButton>}
              {(selected.status === "submitted" || selected.status === "under_review") && <ConfirmButton confirmText="Request changes?" onConfirm={() => transition("changes")}>Request changes</ConfirmButton>}
              {(selected.status === "submitted" || selected.status === "under_review") && <ConfirmButton className="button primary" confirmText="Approve submission?" onConfirm={() => transition("approve")}>Approve</ConfirmButton>}
              {(selected.status === "submitted" || selected.status === "under_review") && <ConfirmButton confirmText="Reject submission?" onConfirm={() => transition("reject")}>Reject</ConfirmButton>}
            </div>
            <h4>Workflow history</h4>
            {events.length === 0 ? <p className="muted">No review events yet.</p> : <ul className="timeline">{events.map((event) => <li key={event.id}><strong>{event.action}</strong> · {event.from_status ?? "new"} → {event.to_status}<span>{event.notes ?? ""}</span></li>)}</ul>}
          </div>
        )}
      </section>
    </div>
  );
}

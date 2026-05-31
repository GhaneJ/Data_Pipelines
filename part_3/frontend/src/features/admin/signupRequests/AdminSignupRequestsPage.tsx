import { FormEvent, useMemo, useState, useEffect } from "react";
import { approveRegistrationRequest, listRegistrationRequests, rejectRegistrationRequest } from "@/api/registrationRequests";
import type { RegistrationRequest, RegistrationStatus } from "@/api/types";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

export function AdminSignupRequestsPage() {
  const [requests, setRequests] = useState<RegistrationRequest[]>([]);
  const [selected, setSelected] = useState<RegistrationRequest | null>(null);
  const [statusFilter, setStatusFilter] = useState<RegistrationStatus | "">("pending");
  const [reviewNotes, setReviewNotes] = useState("Approved for provider workspace access.");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setStatus("loading");
    setError(null);
    try {
      const result = await listRegistrationRequests({ status: statusFilter || undefined, limit: 100 });
      setRequests(result.items);
      setSelected((current) => {
        if (current && result.items.some((request) => request.id === current.id)) return current;
        return result.items[0] ?? null;
      });
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => {
    void load();
  }, [statusFilter]);

  const counts = useMemo(() => {
    return {
      pending: requests.filter((request) => request.status === "pending").length,
      reviewed: requests.filter((request) => request.status !== "pending").length,
      total: requests.length,
    };
  }, [requests]);

  async function approve(request: RegistrationRequest) {
    setError(null);
    setMessage(null);
    try {
      await approveRegistrationRequest(request.id, reviewNotes.trim() || "Approved.");
      setMessage("Access request approved successfully.");
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function reject(request: RegistrationRequest) {
    setError(null);
    setMessage(null);
    try {
      await rejectRegistrationRequest(request.id, reviewNotes.trim() || "Rejected.");
      setMessage("Access request rejected successfully.");
      await load();
    } catch (err) {
      setError(err);
    }
  }

  function selectRequest(request: RegistrationRequest) {
    setSelected(request);
    setReviewNotes(request.status === "pending" ? "Approved for provider workspace access." : request.review_notes ?? "");
    setMessage(null);
    setError(null);
  }

  return (
    <div className="split-grid signup-review-page">
      <section className="panel table-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Controlled access</p>
            <h2>Provider access review</h2>
          </div>
          <label className="inline-filter">Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as RegistrationStatus | "")}>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="">All</option>
            </select>
          </label>
        </div>
        <div className="mini-metric-grid request-metrics">
          <article><span>Loaded</span><strong>{counts.total}</strong></article>
          <article><span>Pending</span><strong>{counts.pending}</strong></article>
          <article><span>Reviewed</span><strong>{counts.reviewed}</strong></article>
        </div>
        <p className="muted">This page is the gate between public access requests and real provider accounts. Approval creates an active provider user; rejection preserves the request history without creating a user.</p>
        {message && <div className="alert alert-success compact-alert">{message}</div>}
        {error !== null && <ErrorPanel error={error} />}
        {status === "loading" && <LoadingState text="Loading provider access requests..." />}
        {status === "success" && requests.length === 0 && <EmptyState title="No requests in this view" text="Change the status filter or create a public provider access request from the signup page." />}
        {status === "success" && requests.length > 0 && (
          <table className="records-table">
            <thead><tr><th>Applicant</th><th>Provider</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id} className={selected?.id === request.id ? "selected-row" : ""} onClick={() => selectRequest(request)}>
                  <td><strong>{request.display_name}</strong><span>{request.requested_username}{request.email ? ` · ${request.email}` : ""}</span></td>
                  <td><strong>{request.organization_name ?? "Provider access"}</strong><span>Provider ID {request.provider_id}</span></td>
                  <td><StatusBadge status={request.status} /></td>
                  <td>{new Date(request.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel detail-panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Review decision</p>
            <h2>{selected ? selected.display_name : "Select a request"}</h2>
          </div>
          {selected && <StatusBadge status={selected.status} />}
        </div>
        {!selected ? (
          <p className="muted">Open an access request to review applicant details and make a decision.</p>
        ) : (
          <form className="detail-stack" onSubmit={(event: FormEvent) => event.preventDefault()}>
            <dl className="metadata polished-metadata">
              <dt>Requested username</dt><dd>{selected.requested_username}</dd>
              <dt>Display name</dt><dd>{selected.display_name}</dd>
              <dt>Email</dt><dd>{selected.email ?? "—"}</dd>
              <dt>Provider</dt><dd>{selected.organization_name ?? "—"}</dd>
              <dt>Provider ID</dt><dd>{selected.provider_id}</dd>
              <dt>Message</dt><dd>{selected.message ?? "—"}</dd>
              <dt>Reviewed at</dt><dd>{selected.reviewed_at ? new Date(selected.reviewed_at).toLocaleString() : "Not reviewed yet"}</dd>
              <dt>Created user</dt><dd>{selected.created_user_id ?? "No user created"}</dd>
            </dl>
            <label className="field wide">Review note
              <textarea
                value={reviewNotes}
                disabled={selected.status !== "pending"}
                onChange={(event) => setReviewNotes(event.target.value)}
              />
            </label>
            {selected.status === "pending" ? (
              <div className="actions action-cluster spacious-actions">
                <ConfirmButton className="button primary" confirmText={`Approve ${selected.requested_username}?`} onConfirm={() => approve(selected)}>Approve access</ConfirmButton>
                <ConfirmButton confirmText={`Reject ${selected.requested_username}?`} onConfirm={() => reject(selected)}>Reject request</ConfirmButton>
              </div>
            ) : (
              <div className="alert alert-info compact-alert">This request has already been reviewed. The decision is preserved for audit/history.</div>
            )}
          </form>
        )}
      </section>
    </div>
  );
}

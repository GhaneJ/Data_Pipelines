import { FormEvent, useEffect, useMemo, useState } from "react";
import { approveRegistrationRequest, listRegistrationRequests, rejectRegistrationRequest } from "@/api/registrationRequests";
import type { RegistrationRequest, RegistrationStatus } from "@/api/types";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

type RequestView = RegistrationStatus | "";

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}

function providerLabel(request: RegistrationRequest) {
  return request.organization_name || `Provider ${request.provider_id}`;
}

export function AdminSignupRequestsPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [requests, setRequests] = useState<RegistrationRequest[]>([]);
  const [selected, setSelected] = useState<RegistrationRequest | null>(null);
  const [statusFilter, setStatusFilter] = useState<RequestView>("pending");
  const [reviewNotes, setReviewNotes] = useState("Approved for provider workspace access.");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load(preferredSelectionId?: string) {
    setStatus("loading");
    setError(null);
    try {
      const result = await listRegistrationRequests({ limit: 100 });
      setRequests(result.items);
      setSelected((current) => {
        const preferred = preferredSelectionId ? result.items.find((request) => request.id === preferredSelectionId) : null;
        if (preferred) return preferred;
        if (current && result.items.some((request) => request.id === current.id)) return result.items.find((request) => request.id === current.id) ?? current;
        const visible = statusFilter ? result.items.filter((request) => request.status === statusFilter) : result.items;
        return visible[0] ?? result.items[0] ?? null;
      });
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => {
    void load();
    // Load the complete queue on mount. Filtering is local so the summary never lies.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredRequests = useMemo(() => {
    if (!statusFilter) return requests;
    return requests.filter((request) => request.status === statusFilter);
  }, [requests, statusFilter]);

  const counts = useMemo(() => {
    return {
      total: requests.length,
      pending: requests.filter((request) => request.status === "pending").length,
      approved: requests.filter((request) => request.status === "approved").length,
      rejected: requests.filter((request) => request.status === "rejected").length,
    };
  }, [requests]);

  async function approve(request: RegistrationRequest) {
    setError(null);
    setMessage(null);
    try {
      await approveRegistrationRequest(request.id, reviewNotes.trim() || "Approved.");
      setMessage("Access request approved successfully.");
      setStatusFilter("approved");
      await load(request.id);
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
      setStatusFilter("rejected");
      await load(request.id);
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

  const emptyText = statusFilter === "pending"
    ? "There are no provider access requests waiting for approval. Use the public request page when you want to demonstrate the controlled onboarding flow."
    : "No access requests match the selected status. Switch to All history to inspect the full onboarding audit trail.";

  return (
    <div className="onboarding-page">
      <section className="panel onboarding-hero-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Controlled provider onboarding</p>
            <h2>Provider access queue</h2>
            <p className="muted">Use this page for external provider applicants who request access through the public portal. For known staff, create the user directly from User management.</p>
          </div>
          <div className="actions onboarding-hero-actions">
            <button type="button" className="button secondary" onClick={() => onNavigate("/signup")}>Open public request page</button>
            <button type="button" className="button ghost" onClick={() => onNavigate("/admin/users")}>Create managed user</button>
          </div>
        </div>
        <div className="onboarding-flow">
          <article>
            <span>1</span>
            <strong>Applicant requests access</strong>
            <p>A provider representative submits username, provider organization, password, and message.</p>
          </article>
          <article>
            <span>2</span>
            <strong>Admin verifies the request</strong>
            <p>Admin checks the organization and decides whether the applicant should become a provider user.</p>
          </article>
          <article>
            <span>3</span>
            <strong>Decision creates history</strong>
            <p>Approval creates an active provider account. Rejection keeps the request as review history.</p>
          </article>
        </div>
      </section>

      <div className="split-grid signup-review-page refined-signup-review">
        <section className="panel table-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Review register</p>
              <h2>Access requests</h2>
            </div>
            <label className="inline-filter">View
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as RequestView)}>
                <option value="pending">Pending approval</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="">All history</option>
              </select>
            </label>
          </div>

          <div className="mini-metric-grid request-metrics onboarding-metrics">
            <article><span>All requests</span><strong>{counts.total}</strong></article>
            <article><span>Pending</span><strong>{counts.pending}</strong></article>
            <article><span>Approved</span><strong>{counts.approved}</strong></article>
            <article><span>Rejected</span><strong>{counts.rejected}</strong></article>
          </div>

          {message && <div className="alert alert-success compact-alert">{message}</div>}
          {error !== null && <ErrorPanel error={error} />}
          {status === "loading" && <LoadingState text="Loading provider access requests..." />}
          {status === "success" && filteredRequests.length === 0 && (
            <EmptyState title={statusFilter === "pending" ? "No pending provider access requests" : "No requests in this view"} text={emptyText} />
          )}
          {status === "success" && filteredRequests.length > 0 && (
            <table className="records-table onboarding-table">
              <thead><tr><th>Applicant</th><th>Provider organization</th><th>Status</th><th>Created</th></tr></thead>
              <tbody>
                {filteredRequests.map((request) => (
                  <tr key={request.id} className={selected?.id === request.id ? "selected-row" : ""} onClick={() => selectRequest(request)}>
                    <td><strong>{request.display_name}</strong><span>{request.requested_username}{request.email ? ` · ${request.email}` : ""}</span></td>
                    <td><strong>{providerLabel(request)}</strong><span>Provider ID {request.provider_id}</span></td>
                    <td><StatusBadge status={request.status} /></td>
                    <td>{formatDate(request.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="panel detail-panel onboarding-decision-panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Decision workspace</p>
              <h2>{selected ? selected.display_name : "What this page is for"}</h2>
            </div>
            {selected && <StatusBadge status={selected.status} />}
          </div>
          {!selected ? (
            <div className="detail-stack">
              <p className="muted">This is an approval queue for provider access requests coming from the public portal. It is intentionally separate from User management.</p>
              <div className="decision-help-grid">
                <article>
                  <strong>Use this page when</strong>
                  <span>an external provider applicant has requested access and should be reviewed before account creation.</span>
                </article>
                <article>
                  <strong>Use User management when</strong>
                  <span>you already know the person and want to create an admin or provider account directly.</span>
                </article>
              </div>
              <div className="actions spacious-actions">
                <button type="button" className="button secondary" onClick={() => onNavigate("/signup")}>Create demo request</button>
                <button type="button" className="button ghost" onClick={() => onNavigate("/admin/users")}>Go to users</button>
              </div>
            </div>
          ) : (
            <form className="detail-stack" onSubmit={(event: FormEvent) => event.preventDefault()}>
              <dl className="metadata polished-metadata onboarding-metadata">
                <dt>Requested username</dt><dd>{selected.requested_username}</dd>
                <dt>Display name</dt><dd>{selected.display_name}</dd>
                <dt>Email</dt><dd>{selected.email ?? "—"}</dd>
                <dt>Provider organization</dt><dd>{providerLabel(selected)}</dd>
                <dt>Provider ID</dt><dd>{selected.provider_id}</dd>
                <dt>Applicant message</dt><dd>{selected.message ?? "—"}</dd>
                <dt>Created</dt><dd>{formatDate(selected.created_at)}</dd>
                <dt>Reviewed</dt><dd>{formatDate(selected.reviewed_at)}</dd>
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
                  <ConfirmButton className="button primary" confirmText={`Approve ${selected.requested_username}?`} onConfirm={() => approve(selected)}>Approve and create provider user</ConfirmButton>
                  <ConfirmButton confirmText={`Reject ${selected.requested_username}?`} onConfirm={() => reject(selected)}>Reject request</ConfirmButton>
                </div>
              ) : (
                <div className="alert alert-info compact-alert">Decision already recorded. This request is preserved as onboarding history.</div>
              )}
            </form>
          )}
        </section>
      </div>
    </div>
  );
}

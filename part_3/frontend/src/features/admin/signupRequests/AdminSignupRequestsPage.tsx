import { useEffect, useState } from "react";
import { approveRegistrationRequest, listRegistrationRequests, rejectRegistrationRequest } from "@/api/registrationRequests";
import type { RegistrationRequest } from "@/api/types";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

export function AdminSignupRequestsPage() {
  const [requests, setRequests] = useState<RegistrationRequest[]>([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);

  async function load() {
    setStatus("loading");
    setError(null);
    try {
      const result = await listRegistrationRequests({ limit: 100 });
      setRequests(result.items);
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function approve(request: RegistrationRequest) {
    const notes = window.prompt(`Approval note for ${request.requested_username}`, "Approved for provider workspace access.") ?? undefined;
    await approveRegistrationRequest(request.id, notes);
    await load();
  }

  async function reject(request: RegistrationRequest) {
    const notes = window.prompt(`Rejection note for ${request.requested_username}`, "Provider access request rejected.") ?? undefined;
    await rejectRegistrationRequest(request.id, notes);
    await load();
  }

  return (
    <section className="panel table-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Controlled signup</p>
          <h2>Provider access requests</h2>
        </div>
        <p className="muted">Public signup creates pending requests only. Approval creates the active provider user.</p>
      </div>
      {error !== null && <ErrorPanel error={error} />}
      {status === "loading" && <LoadingState text="Loading provider access requests..." />}
      {status === "success" && requests.length === 0 && <EmptyState title="No signup requests" text="Pending provider access requests will appear here." />}
      {status === "success" && requests.length > 0 && (
        <table>
          <thead><tr><th>Applicant</th><th>Provider</th><th>Message</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
          <tbody>
            {requests.map((request) => (
              <tr key={request.id}>
                <td><strong>{request.requested_username}</strong><span>{request.display_name}{request.email ? ` · ${request.email}` : ""}</span></td>
                <td>{request.provider_id}<span>{request.organization_name ?? ""}</span></td>
                <td>{request.message ?? "—"}</td>
                <td><StatusBadge status={request.status} /></td>
                <td>{new Date(request.created_at).toLocaleString()}</td>
                <td className="actions">
                  {request.status === "pending" ? (
                    <>
                      <ConfirmButton className="button primary" confirmText={`Approve ${request.requested_username}?`} onConfirm={() => approve(request)}>Approve</ConfirmButton>
                      <ConfirmButton confirmText={`Reject ${request.requested_username}?`} onConfirm={() => reject(request)}>Reject</ConfirmButton>
                    </>
                  ) : (
                    <span className="muted">Reviewed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

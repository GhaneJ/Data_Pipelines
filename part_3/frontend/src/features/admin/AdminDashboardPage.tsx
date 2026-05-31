import { useEffect, useState } from "react";
import { listUsers } from "@/api/adminUsers";
import { listRegistrationRequests } from "@/api/registrationRequests";
import { listAdminProviderSubmissions } from "@/api/adminReviews";
import { ErrorPanel, LoadingState } from "@/components/shared/Feedback";

export function AdminDashboardPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [cards, setCards] = useState({ totalUsers: 0, activeUsers: 0, pendingRequests: 0, pendingReviews: 0, needsChanges: 0 });
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    async function load() {
      try {
        const [users, requests, submitted, needsChanges] = await Promise.all([
          listUsers({ limit: 100 }),
          listRegistrationRequests({ status: "pending", limit: 100 }),
          listAdminProviderSubmissions({ status: "submitted", limit: 100 }),
          listAdminProviderSubmissions({ status: "needs_changes", limit: 100 }),
        ]);
        setCards({ totalUsers: users.items.length, activeUsers: users.items.filter((user) => user.is_active).length, pendingRequests: requests.items.length, pendingReviews: submitted.items.length, needsChanges: needsChanges.items.length });
        setStatus("success");
      } catch (err) {
        setError(err);
        setStatus("error");
      }
    }
    void load();
  }, []);

  return (
    <div className="page-stack">
      <section className="hero compact"><p className="eyebrow">Admin workspace</p><h2>Admin dashboard</h2><p>Manage controlled signup, users, machine API access, and provider review workflow from one browser workspace.</p></section>
      {status === "loading" && <LoadingState text="Loading admin dashboard..." />}
      {error !== null && <ErrorPanel error={error} />}
      {status === "success" && <section className="summary-grid"><button className="summary-tile" onClick={() => onNavigate("/admin/users")}><span>Total users</span><strong>{cards.totalUsers}</strong><small>{cards.activeUsers} active</small></button><button className="summary-tile" onClick={() => onNavigate("/admin/signup-requests")}><span>Pending signup requests</span><strong>{cards.pendingRequests}</strong><small>approval creates provider users</small></button><button className="summary-tile" onClick={() => onNavigate("/admin/provider-submissions")}><span>Pending reviews</span><strong>{cards.pendingReviews}</strong><small>{cards.needsChanges} need changes</small></button><button className="summary-tile" onClick={() => onNavigate("/admin/api-access")}><span>Machine access</span><strong>X-API-Key</strong><small>separate from human login</small></button></section>}
    </div>
  );
}

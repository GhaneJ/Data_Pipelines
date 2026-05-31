import { useEffect, useMemo, useState } from "react";
import { listApiKeys } from "@/api/apiKeys";
import { listUsers } from "@/api/adminUsers";
import { listRegistrationRequests } from "@/api/registrationRequests";
import { listAdminProviderSubmissions } from "@/api/adminReviews";
import { API_BASE_URL } from "@/api/client";
import { getDatabaseHealth, getHealth } from "@/services/api";
import type { DatabaseHealth, HealthStatus } from "@/services/api";
import { ErrorPanel, LoadingState } from "@/components/shared/Feedback";

interface DashboardCards {
  totalUsers: number;
  activeUsers: number;
  inactiveUsers: number;
  adminUsers: number;
  providerUsers: number;
  pendingRequests: number;
  approvedRequests: number;
  rejectedRequests: number;
  pendingReviews: number;
  underReview: number;
  needsChanges: number;
  finalDecisions: number;
  apiKeys: number;
}

const DASHBOARD_QUERY_LIMIT = 100;

const initialCards: DashboardCards = {
  totalUsers: 0,
  activeUsers: 0,
  inactiveUsers: 0,
  adminUsers: 0,
  providerUsers: 0,
  pendingRequests: 0,
  approvedRequests: 0,
  rejectedRequests: 0,
  pendingReviews: 0,
  underReview: 0,
  needsChanges: 0,
  finalDecisions: 0,
  apiKeys: 0,
};

function ratio(part: number, total: number) {
  if (total <= 0) return 0;
  return Math.round((part / total) * 100);
}

function workflowWidth(count: number, maximum: number) {
  if (count <= 0 || maximum <= 0) return 0;
  return Math.max(8, Math.round((count / maximum) * 100));
}

function healthLabel(health: HealthStatus | null, database: DatabaseHealth | null) {
  if (!health || !database) return "Checking";
  if (health.status === "ok" && database.status === "ready") return "Ready";
  return "Needs attention";
}

function StatusPill({ label, ok }: { label: string; ok: boolean }) {
  return <span className={ok ? "status-pill ok" : "status-pill warning"}>{label}</span>;
}

export function AdminDashboardPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [cards, setCards] = useState<DashboardCards>(initialCards);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [databaseHealth, setDatabaseHealth] = useState<DatabaseHealth | null>(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    async function load() {
      try {
        const [users, pendingRequests, approvedRequests, rejectedRequests, submitted, underReview, needsChanges, approved, rejected, keys, healthResult, databaseResult] = await Promise.all([
          listUsers({ limit: DASHBOARD_QUERY_LIMIT }),
          listRegistrationRequests({ status: "pending", limit: DASHBOARD_QUERY_LIMIT }),
          listRegistrationRequests({ status: "approved", limit: DASHBOARD_QUERY_LIMIT }),
          listRegistrationRequests({ status: "rejected", limit: DASHBOARD_QUERY_LIMIT }),
          listAdminProviderSubmissions({ status: "submitted", limit: DASHBOARD_QUERY_LIMIT }),
          listAdminProviderSubmissions({ status: "under_review", limit: DASHBOARD_QUERY_LIMIT }),
          listAdminProviderSubmissions({ status: "needs_changes", limit: DASHBOARD_QUERY_LIMIT }),
          listAdminProviderSubmissions({ status: "approved", limit: DASHBOARD_QUERY_LIMIT }),
          listAdminProviderSubmissions({ status: "rejected", limit: DASHBOARD_QUERY_LIMIT }),
          listApiKeys().catch(() => []),
          getHealth(),
          getDatabaseHealth(),
        ]);

        setCards({
          totalUsers: users.items.length,
          activeUsers: users.items.filter((user) => user.is_active).length,
          inactiveUsers: users.items.filter((user) => !user.is_active).length,
          adminUsers: users.items.filter((user) => user.role === "admin").length,
          providerUsers: users.items.filter((user) => user.role === "provider").length,
          pendingRequests: pendingRequests.items.length,
          approvedRequests: approvedRequests.items.length,
          rejectedRequests: rejectedRequests.items.length,
          pendingReviews: submitted.items.length,
          underReview: underReview.items.length,
          needsChanges: needsChanges.items.length,
          finalDecisions: approved.items.length + rejected.items.length,
          apiKeys: keys.length,
        });
        setHealth(healthResult);
        setDatabaseHealth(databaseResult);
        setStatus("success");
      } catch (err) {
        setError(err);
        setStatus("error");
      }
    }
    void load();
  }, []);

  const activeUserPercent = useMemo(() => ratio(cards.activeUsers, cards.totalUsers), [cards.activeUsers, cards.totalUsers]);
  const adminPercent = useMemo(() => ratio(cards.adminUsers, Math.max(cards.totalUsers, 1)), [cards.adminUsers, cards.totalUsers]);
  const providerPercent = useMemo(() => ratio(cards.providerUsers, Math.max(cards.totalUsers, 1)), [cards.providerUsers, cards.totalUsers]);
  const inactivePercent = useMemo(() => ratio(cards.inactiveUsers, Math.max(cards.totalUsers, 1)), [cards.inactiveUsers, cards.totalUsers]);
  const reviewLoad = cards.pendingReviews + cards.underReview + cards.needsChanges;
  const reviewMaximum = Math.max(cards.pendingReviews, cards.underReview, cards.needsChanges, 1);
  const applicationRows = databaseHealth?.applications?.row_count ?? 0;
  const apiReady = health?.status === "ok";
  const dbReady = databaseHealth?.status === "ready";
  const tablesReady = Boolean(databaseHealth?.required_tables?.ok);

  return (
    <div className="page-stack admin-dashboard-page">
      <section className="hero compact admin-command-hero">
        <div>
          <p className="eyebrow">Admin command center</p>
          <h2>Operational control room</h2>
          <p>Identity, access requests, provider reviews, machine access, and runtime readiness in one clean demo overview.</p>
          <div className="hero-chip-row" aria-label="Runtime health summary">
            <StatusPill label={`API ${apiReady ? "online" : "checking"}`} ok={apiReady} />
            <StatusPill label={`Database ${dbReady ? "ready" : "checking"}`} ok={dbReady} />
            <StatusPill label={`Tables ${tablesReady ? "ready" : "checking"}`} ok={tablesReady} />
          </div>
        </div>
        <div className="system-status-card refined-status-card">
          <span>System status</span>
          <strong>{healthLabel(health, databaseHealth)}</strong>
          <small>{API_BASE_URL}</small>
        </div>
      </section>

      {status === "loading" && <LoadingState text="Loading admin dashboard..." />}
      {error !== null && <ErrorPanel error={error} />}

      {status === "success" && (
        <>
          <section className="admin-insight-grid refined-insight-grid">
            <button className="insight-card" type="button" onClick={() => onNavigate("/admin/users")}>
              <span>Managed users</span>
              <strong>{cards.totalUsers}</strong>
              <small>{cards.activeUsers} active · {cards.inactiveUsers} inactive</small>
            </button>
            <button className="insight-card" type="button" onClick={() => onNavigate("/admin/signup-requests")}>
              <span>Provider access requests</span>
              <strong>{cards.pendingRequests}</strong>
              <small>{cards.approvedRequests} approved · {cards.rejectedRequests} rejected</small>
            </button>
            <button className="insight-card" type="button" onClick={() => onNavigate("/admin/provider-submissions")}>
              <span>Review workload</span>
              <strong>{reviewLoad}</strong>
              <small>{cards.pendingReviews} submitted · {cards.needsChanges} needs changes</small>
            </button>
            <button className="insight-card" type="button" onClick={() => onNavigate("/admin/api-access")}>
              <span>Machine access</span>
              <strong>{cards.apiKeys}</strong>
              <small>Export clients only · not browser login</small>
            </button>
          </section>

          <section className="dashboard-analytics-grid refined-dashboard-grid">
            <article className="panel analytics-panel executive-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Identity health</p>
                  <h3>User composition</h3>
                </div>
              </div>
              <div className="identity-composition-card" aria-label="User composition summary">
                <div className="identity-total">
                  <span>Active users</span>
                  <strong>{activeUserPercent}%</strong>
                  <small>{cards.activeUsers} of {cards.totalUsers} accounts active</small>
                </div>
                <div className="composition-stack" aria-hidden="true">
                  <span className="segment segment-admin" style={{ width: `${Math.max(adminPercent, cards.adminUsers > 0 ? 6 : 0)}%` }} />
                  <span className="segment segment-provider" style={{ width: `${Math.max(providerPercent, cards.providerUsers > 0 ? 6 : 0)}%` }} />
                  <span className="segment segment-inactive" style={{ width: `${Math.max(inactivePercent, cards.inactiveUsers > 0 ? 6 : 0)}%` }} />
                </div>
                <dl className="composition-list">
                  <div><dt><span className="legend-dot legend-admin" />Administrators</dt><dd>{cards.adminUsers}</dd></div>
                  <div><dt><span className="legend-dot legend-provider" />Providers</dt><dd>{cards.providerUsers}</dd></div>
                  <div><dt><span className="legend-dot legend-inactive" />Inactive accounts</dt><dd>{cards.inactiveUsers}</dd></div>
                </dl>
              </div>
            </article>

            <article className="panel analytics-panel executive-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Queue health</p>
                  <h3>Provider workflow</h3>
                </div>
              </div>
              <div className="workflow-meters" aria-label="Provider workflow counts">
                <div className="workflow-meter">
                  <div className="workflow-meter-header"><span>Submitted</span><strong>{cards.pendingReviews}</strong></div>
                  <div className="workflow-track"><span style={{ width: `${workflowWidth(cards.pendingReviews, reviewMaximum)}%` }} /></div>
                </div>
                <div className="workflow-meter">
                  <div className="workflow-meter-header"><span>Under review</span><strong>{cards.underReview}</strong></div>
                  <div className="workflow-track"><span style={{ width: `${workflowWidth(cards.underReview, reviewMaximum)}%` }} /></div>
                </div>
                <div className="workflow-meter">
                  <div className="workflow-meter-header"><span>Needs changes</span><strong>{cards.needsChanges}</strong></div>
                  <div className="workflow-track"><span style={{ width: `${workflowWidth(cards.needsChanges, reviewMaximum)}%` }} /></div>
                </div>
              </div>
              <small className="muted">{cards.finalDecisions} final decision{cards.finalDecisions === 1 ? "" : "s"} are preserved as review history.</small>
            </article>

            <article className="panel analytics-panel executive-panel system-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Runtime readiness</p>
                  <h3>API and database</h3>
                </div>
              </div>
              <dl className="system-check-list">
                <div><dt>API</dt><dd className={apiReady ? "ok-text" : "warning-text"}>{health?.status ?? "checking"}</dd></div>
                <div><dt>Database</dt><dd className={dbReady ? "ok-text" : "warning-text"}>{databaseHealth?.status ?? "checking"}</dd></div>
                <div><dt>Applications</dt><dd>{applicationRows.toLocaleString("sv-SE")} rows</dd></div>
                <div><dt>Required tables</dt><dd>{tablesReady ? "ready" : "needs check"}</dd></div>
              </dl>
            </article>
          </section>

          <section className="admin-action-grid">
            <article className="panel action-panel">
              <p className="eyebrow">Access operations</p>
              <h3>Provider onboarding</h3>
              <p>Review pending provider access requests and create managed users when access should be handled directly by an administrator.</p>
              <div className="action-cluster">
                <button className="button primary" type="button" onClick={() => onNavigate("/admin/signup-requests")}>Review access requests</button>
                <button className="button secondary" type="button" onClick={() => onNavigate("/admin/users")}>Manage users</button>
              </div>
            </article>
            <article className="panel action-panel machine-access-panel">
              <p className="eyebrow">Machine access</p>
              <h3>API keys and export boundary</h3>
              <p>Machine clients use scoped API keys for export access. Browser users continue to use personal sessions.</p>
              <button className="button secondary" type="button" onClick={() => onNavigate("/admin/api-access")}>Open machine access</button>
            </article>
            <article className="panel action-panel">
              <p className="eyebrow">Source operations</p>
              <h3>MYH monitoring and refresh</h3>
              <p>Check the official MYH result page, review detected files, inspect notifications, and import validated official source data.</p>
              <button className="button secondary" type="button" onClick={() => onNavigate("/admin/operations")}>Open operations</button>
            </article>
          </section>
        </>
      )}
    </div>
  );
}

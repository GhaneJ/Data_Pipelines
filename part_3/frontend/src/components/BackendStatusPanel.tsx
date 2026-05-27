import type { ApiStatus, DatabaseHealth, HealthStatus } from "../services/api";

interface BackendStatusPanelProps {
  apiBaseUrl: string;
  healthStatus: ApiStatus;
  dbStatus: ApiStatus;
  health: HealthStatus | null;
  databaseHealth: DatabaseHealth | null;
  errorMessage: string | null;
}

function statusLabel(status: ApiStatus, target: "api" | "database"): string {
  if (status === "loading") return "Checking";
  if (status === "success") return "Reachable";
  if (status === "error") return target === "api" ? "Offline" : "Needs attention";
  return "Not checked";
}

export function BackendStatusPanel({
  apiBaseUrl,
  healthStatus,
  dbStatus,
  health,
  databaseHealth,
  errorMessage,
}: BackendStatusPanelProps) {
  const applicationRows = databaseHealth?.applications?.row_count ?? null;

  return (
    <section className="status-panel" aria-labelledby="backend-status-title">
      <div>
        <p className="eyebrow">API connection</p>
        <h2 id="backend-status-title">Backend status</h2>
        <p className="muted">Using public FastAPI endpoints from {apiBaseUrl}</p>
      </div>

      <div className="status-grid">
        <article className={`status-pill status-${healthStatus}`}>
          <span>API</span>
          <strong>{statusLabel(healthStatus, "api")}</strong>
          {health && <small>Response: {health.status}</small>}
        </article>
        <article className={`status-pill status-${dbStatus}`}>
          <span>Database</span>
          <strong>{statusLabel(dbStatus, "database")}</strong>
          {applicationRows !== null && <small>{applicationRows.toLocaleString()} application rows</small>}
        </article>
      </div>

      {errorMessage && (
        <p className="callout warning" role="alert">
          {errorMessage}
        </p>
      )}
    </section>
  );
}

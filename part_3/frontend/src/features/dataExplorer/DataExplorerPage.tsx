import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, getDatabaseHealth, getHealth } from "@/services/api";
import type { ApiStatus, DatabaseHealth, HealthStatus } from "@/services/api";
import { ApplicationsBrowser } from "@/components/ApplicationsBrowser";
import { CategoryBars } from "@/components/CategoryBars";
import { DecisionTrendChart } from "@/components/DecisionTrendChart";
import { StateMessage } from "@/components/StateMessage";
import { SummaryCards } from "@/components/SummaryCards";
import { YearTrendChart } from "@/components/YearTrendChart";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";

function statusText(status: ApiStatus): string {
  if (status === "loading") return "Checking";
  if (status === "success") return "Online";
  if (status === "error") return "Needs attention";
  return "Waiting";
}

export function DataExplorerPage() {
  const [healthStatus, setHealthStatus] = useState<ApiStatus>("idle");
  const [dbStatus, setDbStatus] = useState<ApiStatus>("idle");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [databaseHealth, setDatabaseHealth] = useState<DatabaseHealth | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const metrics = useDashboardMetrics();

  useEffect(() => {
    let isActive = true;
    async function checkBackend() {
      setHealthStatus("loading");
      setDbStatus("loading");
      try {
        const healthResult = await getHealth();
        if (!isActive) return;
        setHealth(healthResult);
        setHealthStatus("success");
        const databaseResult = await getDatabaseHealth();
        if (!isActive) return;
        setDatabaseHealth(databaseResult);
        setDbStatus(databaseResult.status === "ready" ? "success" : "error");
      } catch {
        if (!isActive) return;
        setHealthStatus("error");
        setDbStatus("idle");
        setErrorMessage(`Could not reach the FastAPI backend at ${API_BASE_URL}. Start the backend from part_3 and confirm /health/db before the demo.`);
      }
    }
    checkBackend();
    return () => {
      isActive = false;
    };
  }, []);

  const dataStory = useMemo(() => {
    const yearCount = metrics.yearStats.length;
    const firstYear = metrics.yearStats[0]?.source_year;
    const lastYear = metrics.yearStats.at(-1)?.source_year;
    return {
      rowCount: databaseHealth?.applications?.row_count ?? null,
      yearRange: firstYear && lastYear ? `${firstYear}-${lastYear}` : yearCount > 0 ? `${yearCount} years` : "Waiting for data",
      apiStatus: health?.status ?? statusText(healthStatus),
      dbStatus: statusText(dbStatus),
    };
  }, [databaseHealth, dbStatus, health, healthStatus, metrics.yearStats]);

  return (
    <div className="page-stack data-explorer">
      <section className="data-hero">
        <div className="data-hero-copy">
          <p className="eyebrow">Public data explorer</p>
          <h2>MYH applications intelligence</h2>
          <p>
            A read-only intelligence view for official MYH application history, with clean filters, compact trends, and live API/database status for the demo.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="#applications-browser-title">Browse applications</a>
            <a className="button secondary" href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">Open API docs</a>
          </div>
        </div>
        <div className="data-health-card" aria-label="Backend status summary">
          <span>Connected API</span>
          <strong>{API_BASE_URL}</strong>
          <div className="health-grid">
            <article className={`health-tile health-${healthStatus}`}><span>API</span><strong>{dataStory.apiStatus}</strong></article>
            <article className={`health-tile health-${dbStatus}`}><span>Database</span><strong>{dataStory.dbStatus}</strong></article>
          </div>
          {errorMessage && <p className="callout warning" role="alert">{errorMessage}</p>}
        </div>
      </section>

      <section className="kpi-ribbon" aria-label="Data explorer key facts">
        <article><span>Application rows</span><strong>{dataStory.rowCount !== null ? dataStory.rowCount.toLocaleString("sv-SE") : "—"}</strong><small>from PostgreSQL</small></article>
        <article><span>Source years</span><strong>{dataStory.yearRange}</strong><small>MYH Tabell 3 backbone</small></article>
        <article><span>Access model</span><strong>Public read</strong><small>no browser API key</small></article>
        <article><span>Workflow data</span><strong>Separated</strong><small>submissions are not official history</small></article>
      </section>

      <section className="dashboard-section data-story-panel" aria-labelledby="summary-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Executive overview</p>
            <h2 id="summary-title">Applications intelligence</h2>
          </div>
          <p className="muted">Official historical applications are summarized separately from provider workflow drafts and reviews.</p>
        </div>
        <StateMessage
          status={metrics.status}
          errorText={metrics.errorMessage}
          isEmpty={metrics.yearStats.length === 0}
          emptyText="No statistics were returned by the backend."
        />
        {metrics.status === "success" && metrics.yearStats.length > 0 && (
          <>
            <SummaryCards yearStats={metrics.yearStats} decisionStats={metrics.decisionStats} />
            <section className="chart-grid premium-chart-grid" aria-label="Trend charts">
              <YearTrendChart data={metrics.yearStats} />
              <DecisionTrendChart data={metrics.decisionTrend} />
            </section>
            <CategoryBars regions={metrics.regionStats} educationAreas={metrics.educationAreaStats} />
          </>
        )}
      </section>

      <ApplicationsBrowser />
    </div>
  );
}

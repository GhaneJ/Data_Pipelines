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

export type DataExplorerView = "overview" | "stats" | "applications";

function statusText(status: ApiStatus): string {
  if (status === "loading") return "Checking";
  if (status === "success") return "Online";
  if (status === "error") return "Needs attention";
  return "Waiting";
}

function PublicDataHero({
  apiStatus,
  dbStatus,
  errorMessage,
  onNavigate,
}: {
  apiStatus: string;
  dbStatus: string;
  errorMessage: string | null;
  onNavigate: (path: string) => void;
}) {
  return (
    <section className="data-hero compact-public-hero">
      <div className="data-hero-copy">
        <p className="eyebrow">Public data portal</p>
        <h2>MYH applications intelligence</h2>
        <p>
          A clean read-only entry point for official MYH application history. Start with the overview, inspect trends, then browse the underlying records.
        </p>
        <div className="hero-actions">
          <button className="button primary" type="button" onClick={() => onNavigate("/data/stats")}>View intelligence</button>
          <button className="button secondary" type="button" onClick={() => onNavigate("/data/applications")}>Browse records</button>
          <a className="button secondary" href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">Open API docs</a>
        </div>
      </div>
      <div className="data-health-card" aria-label="Backend status summary">
        <span>Connected API</span>
        <strong>{API_BASE_URL}</strong>
        <div className="health-grid">
          <article className={`health-tile health-${apiStatus === "Online" ? "success" : apiStatus === "Needs attention" ? "error" : "loading"}`}><span>API</span><strong>{apiStatus}</strong></article>
          <article className={`health-tile health-${dbStatus === "Online" ? "success" : dbStatus === "Needs attention" ? "error" : "loading"}`}><span>Database</span><strong>{dbStatus}</strong></article>
        </div>
        {errorMessage && <p className="callout warning" role="alert">{errorMessage}</p>}
      </div>
    </section>
  );
}

function PublicDataTabs({ active, onNavigate }: { active: DataExplorerView; onNavigate: (path: string) => void }) {
  const tabs: Array<{ key: DataExplorerView; label: string; path: string; note: string }> = [
    { key: "overview", label: "Overview", path: "/data", note: "readiness and story" },
    { key: "stats", label: "Intelligence", path: "/data/stats", note: "charts and trends" },
    { key: "applications", label: "Applications", path: "/data/applications", note: "filter and inspect records" },
  ];

  return (
    <nav className="public-data-tabs" aria-label="Public data sections">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={active === tab.key ? "public-data-tab active" : "public-data-tab"}
          onClick={() => onNavigate(tab.path)}
        >
          <strong>{tab.label}</strong>
          <span>{tab.note}</span>
        </button>
      ))}
    </nav>
  );
}

function KeyFacts({ rowCount, yearRange }: { rowCount: number | null; yearRange: string }) {
  return (
    <section className="kpi-ribbon public-kpi-ribbon" aria-label="Public data key facts">
      <article><span>Application rows</span><strong>{rowCount !== null ? rowCount.toLocaleString("sv-SE") : "—"}</strong><small>from PostgreSQL</small></article>
      <article><span>Source years</span><strong>{yearRange}</strong><small>MYH Tabell 3 backbone</small></article>
      <article><span>Access model</span><strong>Public read</strong><small>no browser API key</small></article>
      <article><span>Workflow data</span><strong>Separated</strong><small>provider submissions are separate</small></article>
    </section>
  );
}

function DataOverview({
  rowCount,
  yearRange,
  apiStatus,
  dbStatus,
  metrics,
  onNavigate,
}: {
  rowCount: number | null;
  yearRange: string;
  apiStatus: string;
  dbStatus: string;
  metrics: ReturnType<typeof useDashboardMetrics>;
  onNavigate: (path: string) => void;
}) {
  const latestYear = metrics.yearStats.at(-1);
  const approvedTotal = metrics.decisionStats.find((item) => item.decision_code === "approved")?.total_applications ?? 0;
  const rejectedTotal = metrics.decisionStats.find((item) => item.decision_code === "rejected")?.total_applications ?? 0;
  const topRegion = metrics.regionStats[0];
  const topArea = metrics.educationAreaStats[0];

  return (
    <>
      <KeyFacts rowCount={rowCount} yearRange={yearRange} />
      <section className="public-overview-grid" aria-label="Public data overview">
        <article className="public-overview-card highlight-card">
          <p className="eyebrow">Data story</p>
          <h2>Official application history</h2>
          <p>
            Explore the curated historical dataset without mixing it with provider workflow drafts. Use the intelligence page for trends and the browser page for individual records.
          </p>
          <div className="overview-actions">
            <button className="button primary" type="button" onClick={() => onNavigate("/data/stats")}>Open intelligence</button>
            <button className="button secondary" type="button" onClick={() => onNavigate("/data/applications")}>Browse applications</button>
          </div>
        </article>
        <article className="public-overview-card">
          <p className="eyebrow">Readiness</p>
          <h3>API and database</h3>
          <dl className="compact-definition-list">
            <div><dt>API</dt><dd>{apiStatus}</dd></div>
            <div><dt>Database</dt><dd>{dbStatus}</dd></div>
            <div><dt>Rows</dt><dd>{rowCount !== null ? rowCount.toLocaleString("sv-SE") : "—"}</dd></div>
          </dl>
        </article>
        <article className="public-overview-card">
          <p className="eyebrow">Latest year</p>
          <h3>{latestYear?.source_year ?? "—"}</h3>
          <p className="big-stat">{latestYear?.total_applications.toLocaleString("sv-SE") ?? "—"}</p>
          <small>applications in the latest loaded source year</small>
        </article>
        <article className="public-overview-card">
          <p className="eyebrow">Decision mix</p>
          <h3>Approved / rejected</h3>
          <p className="big-stat">{approvedTotal.toLocaleString("sv-SE")} / {rejectedTotal.toLocaleString("sv-SE")}</p>
          <small>from normalized decision codes</small>
        </article>
        <article className="public-overview-card">
          <p className="eyebrow">Top region</p>
          <h3>{topRegion?.lan ?? "—"}</h3>
          <p className="big-stat">{topRegion?.total_applications.toLocaleString("sv-SE") ?? "—"}</p>
          <small>applications in the current dataset</small>
        </article>
        <article className="public-overview-card">
          <p className="eyebrow">Top education area</p>
          <h3>{topArea?.utbildningsomrade ?? "—"}</h3>
          <p className="big-stat">{topArea?.total_applications.toLocaleString("sv-SE") ?? "—"}</p>
          <small>applications in the current dataset</small>
        </article>
      </section>
    </>
  );
}

function DataStats({ metrics }: { metrics: ReturnType<typeof useDashboardMetrics> }) {
  return (
    <section className="dashboard-section data-story-panel compact-stats-page" aria-labelledby="summary-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Applications intelligence</p>
          <h2 id="summary-title">Trends and distribution</h2>
        </div>
        <p className="muted">A focused statistics page for annual volume, decision trends, regions, and education areas.</p>
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
  );
}

export function DataExplorerPage({ view = "overview", onNavigate }: { view?: DataExplorerView; onNavigate: (path: string) => void }) {
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
      apiStatus: health?.status === "ok" ? "Online" : statusText(healthStatus),
      dbStatus: statusText(dbStatus),
    };
  }, [databaseHealth, dbStatus, health, healthStatus, metrics.yearStats]);

  return (
    <div className="page-stack data-explorer split-public-data-page">
      <PublicDataHero apiStatus={dataStory.apiStatus} dbStatus={dataStory.dbStatus} errorMessage={errorMessage} onNavigate={onNavigate} />
      <PublicDataTabs active={view} onNavigate={onNavigate} />

      {view === "overview" && (
        <DataOverview
          rowCount={dataStory.rowCount}
          yearRange={dataStory.yearRange}
          apiStatus={dataStory.apiStatus}
          dbStatus={dataStory.dbStatus}
          metrics={metrics}
          onNavigate={onNavigate}
        />
      )}

      {view === "stats" && <DataStats metrics={metrics} />}

      {view === "applications" && <ApplicationsBrowser />}
    </div>
  );
}

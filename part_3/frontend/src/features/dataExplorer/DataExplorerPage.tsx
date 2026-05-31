import { useMemo } from "react";
import { ApplicationsBrowser } from "@/components/ApplicationsBrowser";
import { CategoryBars } from "@/components/CategoryBars";
import { DecisionTrendChart } from "@/components/DecisionTrendChart";
import { StateMessage } from "@/components/StateMessage";
import { SummaryCards } from "@/components/SummaryCards";
import { YearTrendChart } from "@/components/YearTrendChart";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";

export type DataExplorerView = "overview" | "stats" | "applications";

function PublicDataHero({ onNavigate }: { onNavigate: (path: string) => void }) {
  return (
    <section className="data-hero compact-public-hero open-data-hero">
      <div className="data-hero-copy">
        <p className="eyebrow">Open data portal</p>
        <h2>Historical MYH applications, ready to explore</h2>
        <p>
          Explore the curated public application history from MYH. The portal separates official historical records from internal provider drafts, reviews, users, and machine-access administration.
        </p>
        <div className="hero-actions">
          <button className="button primary" type="button" onClick={() => onNavigate("/data/stats")}>View insights</button>
          <button className="button secondary" type="button" onClick={() => onNavigate("/data/applications")}>Browse archive</button>
          <button className="button ghost light" type="button" onClick={() => onNavigate("/signup")}>Request provider access</button>
        </div>
      </div>
      <div className="public-audience-card" aria-label="Public access summary">
        <p className="eyebrow">Public access</p>
        <h3>Open, read-only, historical</h3>
        <p>
          Visitors can explore official application history. Providers and administrators sign in for drafts, reviews, onboarding, users, and machine-access operations.
        </p>
        <div className="public-access-list">
          <span>✓ Historical data</span>
          <span>✓ Trends and filters</span>
          <span>✓ No workflow records</span>
        </div>
      </div>
    </section>
  );
}

function PublicDataTabs({ active, onNavigate }: { active: DataExplorerView; onNavigate: (path: string) => void }) {
  const tabs: Array<{ key: DataExplorerView; label: string; path: string; note: string }> = [
    { key: "overview", label: "Open data", path: "/data", note: "scope and key facts" },
    { key: "stats", label: "Insights", path: "/data/stats", note: "charts and trends" },
    { key: "applications", label: "Archive", path: "/data/applications", note: "filter and inspect records" },
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
    <section className="kpi-ribbon public-kpi-ribbon" aria-label="Open data key facts">
      <article><span>Historical records</span><strong>{rowCount !== null ? rowCount.toLocaleString("sv-SE") : "—"}</strong><small>curated MYH applications</small></article>
      <article><span>Source years</span><strong>{yearRange}</strong><small>Tabell 3 harmonized over time</small></article>
      <article><span>Public layer</span><strong>Read-only</strong><small>safe for visitors and demos</small></article>
      <article><span>Internal workflow</span><strong>Signed in</strong><small>providers and admins only</small></article>
    </section>
  );
}

function DataOverview({
  rowCount,
  yearRange,
  metrics,
  onNavigate,
}: {
  rowCount: number | null;
  yearRange: string;
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
      <section className="public-overview-grid" aria-label="Open data overview">
        <article className="public-overview-card highlight-card">
          <p className="eyebrow">Data story</p>
          <h2>Official application history</h2>
          <p>
            This public area focuses on the historical MYH dataset: years, regions, education areas, decisions, providers, and individual application records. Internal access requests, user administration, API keys, and provider review workflows are kept behind login.
          </p>
          <div className="overview-actions">
            <button className="button primary" type="button" onClick={() => onNavigate("/data/stats")}>Open insights</button>
            <button className="button secondary" type="button" onClick={() => onNavigate("/data/applications")}>Browse archive</button>
          </div>
        </article>
        <article className="public-overview-card">
          <p className="eyebrow">Public scope</p>
          <h3>What visitors can see</h3>
          <dl className="compact-definition-list">
            <div><dt>Records</dt><dd>Historical MYH applications</dd></div>
            <div><dt>Charts</dt><dd>Aggregated public trends</dd></div>
            <div><dt>Protected</dt><dd>Users, drafts, reviews, API keys</dd></div>
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
          <p className="eyebrow">Historical insights</p>
          <h2 id="summary-title">Trends and distribution</h2>
        </div>
        <p className="muted">A public statistics page for annual volume, decision trends, regions, and education areas.</p>
      </div>
      <StateMessage
        status={metrics.status}
        errorText={metrics.errorMessage}
        isEmpty={metrics.yearStats.length === 0}
        emptyText="No statistics were returned by the public API."
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
  const metrics = useDashboardMetrics();

  const dataStory = useMemo(() => {
    const yearCount = metrics.yearStats.length;
    const firstYear = metrics.yearStats[0]?.source_year;
    const lastYear = metrics.yearStats.at(-1)?.source_year;
    const rowCount = metrics.yearStats.reduce((sum, item) => sum + item.total_applications, 0);
    return {
      rowCount: metrics.yearStats.length > 0 ? rowCount : null,
      yearRange: firstYear && lastYear ? `${firstYear}-${lastYear}` : yearCount > 0 ? `${yearCount} years` : "Waiting for data",
    };
  }, [metrics.yearStats]);

  return (
    <div className="page-stack data-explorer split-public-data-page public-open-data-page">
      <PublicDataHero onNavigate={onNavigate} />
      <PublicDataTabs active={view} onNavigate={onNavigate} />

      {view === "overview" && (
        <DataOverview
          rowCount={dataStory.rowCount}
          yearRange={dataStory.yearRange}
          metrics={metrics}
          onNavigate={onNavigate}
        />
      )}

      {view === "stats" && <DataStats metrics={metrics} />}

      {view === "applications" && <ApplicationsBrowser />}
    </div>
  );
}

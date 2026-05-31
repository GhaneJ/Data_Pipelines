import { useEffect, useState } from "react";
import { API_BASE_URL, getDatabaseHealth, getHealth } from "@/services/api";
import type { ApiStatus, DatabaseHealth, HealthStatus } from "@/services/api";
import { ApplicationsBrowser } from "@/components/ApplicationsBrowser";
import { BackendStatusPanel } from "@/components/BackendStatusPanel";
import { CategoryBars } from "@/components/CategoryBars";
import { DecisionTrendChart } from "@/components/DecisionTrendChart";
import { StateMessage } from "@/components/StateMessage";
import { SummaryCards } from "@/components/SummaryCards";
import { YearTrendChart } from "@/components/YearTrendChart";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";

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

  return (
    <div className="page-stack">
      <section className="hero compact">
        <div>
          <p className="eyebrow">Public data explorer</p>
          <h2>MYH Applications Dashboard</h2>
          <p>Public read/statistics endpoints remain open and separate from provider-created workflow submissions.</p>
        </div>
      </section>
      <BackendStatusPanel
        apiBaseUrl={API_BASE_URL}
        healthStatus={healthStatus}
        dbStatus={dbStatus}
        health={health}
        databaseHealth={databaseHealth}
        errorMessage={errorMessage}
      />
      <section className="dashboard-section" aria-labelledby="summary-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Overview</p>
            <h2 id="summary-title">Curated application story</h2>
          </div>
          <p className="muted">Historical MYH data is read from public backend aggregation endpoints.</p>
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
            <section className="chart-grid" aria-label="Trend charts">
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

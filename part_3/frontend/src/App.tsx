import { useEffect, useState } from "react";
import { API_BASE_URL, getDatabaseHealth, getHealth } from "./services/api";
import type { ApiStatus, DatabaseHealth, HealthStatus } from "./services/api";
import { BackendStatusPanel } from "./components/BackendStatusPanel";
import { CategoryBars } from "./components/CategoryBars";
import { DecisionTrendChart } from "./components/DecisionTrendChart";
import { StateMessage } from "./components/StateMessage";
import { SummaryCards } from "./components/SummaryCards";
import { YearTrendChart } from "./components/YearTrendChart";
import { useDashboardMetrics } from "./hooks/useDashboardMetrics";
import "./styles.css";

function App() {
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
      setErrorMessage(null);

      try {
        const healthResult = await getHealth();
        if (!isActive) return;
        setHealth(healthResult);
        setHealthStatus("success");
      } catch (error) {
        if (!isActive) return;
        setHealthStatus("error");
        setDbStatus("error");
        setErrorMessage(error instanceof Error ? error.message : "The backend could not be reached.");
        return;
      }

      try {
        const databaseResult = await getDatabaseHealth();
        if (!isActive) return;
        setDatabaseHealth(databaseResult);
        setDbStatus(databaseResult.status === "ready" ? "success" : "error");
      } catch (error) {
        if (!isActive) return;
        setDbStatus("error");
        setErrorMessage(error instanceof Error ? error.message : "The database readiness check failed.");
      }
    }

    checkBackend();

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Data Pipeline Project — Part 3</p>
          <h1>MYH Applications Dashboard</h1>
          <p>
            A React and TypeScript frontend for presenting the curated MYH applications dataset through the existing
            FastAPI backend.
          </p>
        </div>
      </header>

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
          <p className="muted">Summary cards and charts use backend aggregation endpoints instead of hardcoded data.</p>
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
    </main>
  );
}

export default App;

import { useEffect, useMemo, useState } from "react";
import {
  getStatsByDecision,
  getStatsByEducationArea,
  getStatsByRegion,
  getStatsByYear,
  getTrendByDecision,
  getTrendByEducationArea,
} from "@/services/api";
import type {
  ApiStatus,
  DecisionStats,
  DecisionTrend,
  EducationAreaStats,
  EducationAreaTrend,
  RegionStats,
  YearStats,
} from "@/services/api";

export interface DashboardMetricsState {
  status: ApiStatus;
  yearStats: YearStats[];
  decisionStats: DecisionStats[];
  regionStats: RegionStats[];
  educationAreaStats: EducationAreaStats[];
  decisionTrend: DecisionTrend[];
  educationAreaTrend: EducationAreaTrend[];
  errorMessage: string | null;
}

export function useDashboardMetrics(): DashboardMetricsState {
  const [status, setStatus] = useState<ApiStatus>("idle");
  const [yearStats, setYearStats] = useState<YearStats[]>([]);
  const [decisionStats, setDecisionStats] = useState<DecisionStats[]>([]);
  const [regionStats, setRegionStats] = useState<RegionStats[]>([]);
  const [educationAreaStats, setEducationAreaStats] = useState<EducationAreaStats[]>([]);
  const [decisionTrend, setDecisionTrend] = useState<DecisionTrend[]>([]);
  const [educationAreaTrend, setEducationAreaTrend] = useState<EducationAreaTrend[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadMetrics() {
      setStatus("loading");
      setErrorMessage(null);

      try {
        const [yearRows, decisionRows, regionRows, educationRows, decisionTrendRows, educationTrendRows] =
          await Promise.all([
            getStatsByYear(),
            getStatsByDecision(),
            getStatsByRegion(),
            getStatsByEducationArea(),
            getTrendByDecision({ year_from: 2020, year_to: 2025 }),
            getTrendByEducationArea({ year_from: 2020, year_to: 2025, limit: 6 }),
          ]);

        if (!isActive) return;
        setYearStats(yearRows);
        setDecisionStats(decisionRows);
        setRegionStats(regionRows);
        setEducationAreaStats(educationRows);
        setDecisionTrend(decisionTrendRows);
        setEducationAreaTrend(educationTrendRows);
        setStatus("success");
      } catch (error) {
        if (!isActive) return;
        setStatus("error");
        setErrorMessage(error instanceof Error ? error.message : "Dashboard metrics could not be loaded.");
      }
    }

    loadMetrics();

    return () => {
      isActive = false;
    };
  }, []);

  return useMemo(
    () => ({
      status,
      yearStats,
      decisionStats,
      regionStats,
      educationAreaStats,
      decisionTrend,
      educationAreaTrend,
      errorMessage,
    }),
    [status, yearStats, decisionStats, regionStats, educationAreaStats, decisionTrend, educationAreaTrend, errorMessage],
  );
}

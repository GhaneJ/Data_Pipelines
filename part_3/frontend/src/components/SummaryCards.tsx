import type { DecisionStats, YearStats } from "@/services/api";

interface SummaryCardsProps {
  yearStats: YearStats[];
  decisionStats: DecisionStats[];
}

function formatNumber(value: number): string {
  return value.toLocaleString("sv-SE");
}

function formatPercent(value: number): string {
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 1 })}%`;
}

export function SummaryCards({ yearStats, decisionStats }: SummaryCardsProps) {
  const totalApplications = yearStats.reduce((sum, row) => sum + row.total_applications, 0);
  const approved = decisionStats.find((row) => row.decision_code === "approved")?.total_applications ?? 0;
  const rejected = decisionStats.find((row) => row.decision_code === "rejected")?.total_applications ?? 0;
  const firstYear = yearStats[0]?.source_year;
  const lastYear = yearStats.at(-1)?.source_year;
  const firstApprovalRate = yearStats[0]?.approval_rate_percent ?? 0;
  const lastApprovalRate = yearStats.at(-1)?.approval_rate_percent ?? 0;
  const approvalRateChange = lastApprovalRate - firstApprovalRate;

  return (
    <section className="cards-grid" aria-label="Dashboard summary cards">
      <article className="card metric-card">
        <span>Total applications</span>
        <strong>{formatNumber(totalApplications)}</strong>
        <small>Loaded through /stats/by-year</small>
      </article>
      <article className="card metric-card">
        <span>Approved / rejected</span>
        <strong>
          {formatNumber(approved)} / {formatNumber(rejected)}
        </strong>
        <small>From normalized decision codes</small>
      </article>
      <article className="card metric-card">
        <span>Year range</span>
        <strong>{firstYear && lastYear ? `${firstYear}-${lastYear}` : "-"}</strong>
        <small>Based on source_year</small>
      </article>
      <article className="card metric-card">
        <span>Approval-rate trend</span>
        <strong>{approvalRateChange >= 0 ? "+" : ""}{formatPercent(approvalRateChange)}</strong>
        <small>{formatPercent(firstApprovalRate)} to {formatPercent(lastApprovalRate)}</small>
      </article>
    </section>
  );
}

import { Line, LineChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DecisionTrend } from "../services/api";

interface DecisionTrendChartProps {
  data: DecisionTrend[];
}

interface ChartRow {
  source_year: number;
  approved?: number;
  rejected?: number;
  withdrawn?: number;
}

function pivotDecisionTrend(rows: DecisionTrend[]): ChartRow[] {
  const byYear = new Map<number, ChartRow>();

  rows.forEach((row) => {
    const current = byYear.get(row.source_year) ?? { source_year: row.source_year };
    current[row.decision_code as "approved" | "rejected" | "withdrawn"] = row.application_count;
    byYear.set(row.source_year, current);
  });

  return Array.from(byYear.values()).sort((a, b) => a.source_year - b.source_year);
}

export function DecisionTrendChart({ data }: DecisionTrendChartProps) {
  const chartData = pivotDecisionTrend(data);

  return (
    <article className="chart-card">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Decision trend</p>
          <h2>Decision counts by year</h2>
        </div>
        <p className="muted">Chart-friendly rows from /stats/trends/by-decision.</p>
      </div>
      <div className="chart-frame" aria-label="Decision trend chart">
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={chartData} margin={{ top: 18, right: 24, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#dbe3ec" strokeDasharray="3 3" />
            <XAxis dataKey="source_year" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="approved" name="Approved" stroke="#3d8b5f" strokeWidth={3} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="rejected" name="Rejected" stroke="#c9852b" strokeWidth={3} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="withdrawn" name="Withdrawn" stroke="#7567a8" strokeWidth={3} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

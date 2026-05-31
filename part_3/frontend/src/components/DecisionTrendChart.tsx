import { Line, LineChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DecisionTrend } from "@/services/api";

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
    <article className="chart-card delicate-chart-card">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Decision trend</p>
          <h2>Decision counts by year</h2>
        </div>
        <p className="muted">Approved, rejected, and withdrawn decisions over time.</p>
      </div>
      <div className="chart-frame compact-chart-frame" aria-label="Decision trend chart">
        <ResponsiveContainer width="100%" height={210}>
          <LineChart data={chartData} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#edf3f8" strokeDasharray="2 6" vertical={false} />
            <XAxis dataKey="source_year" tickLine={false} axisLine={false} tick={{ fill: "#64748b", fontSize: 11 }} />
            <YAxis tickLine={false} axisLine={false} width={38} tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <Tooltip />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
            <Line type="monotone" dataKey="approved" name="Approved" stroke="#4f9f7a" strokeWidth={1.8} dot={{ r: 2.4, strokeWidth: 1 }} activeDot={{ r: 4 }} />
            <Line type="monotone" dataKey="rejected" name="Rejected" stroke="#d59a58" strokeWidth={1.8} dot={{ r: 2.4, strokeWidth: 1 }} activeDot={{ r: 4 }} />
            <Line type="monotone" dataKey="withdrawn" name="Withdrawn" stroke="#8b7cc2" strokeWidth={1.8} dot={{ r: 2.4, strokeWidth: 1 }} activeDot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

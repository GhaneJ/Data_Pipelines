import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { YearStats } from "@/services/api";

interface YearTrendChartProps {
  data: YearStats[];
}

export function YearTrendChart({ data }: YearTrendChartProps) {
  return (
    <article className="chart-card delicate-chart-card">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Trend</p>
          <h2>Applications by year</h2>
        </div>
        <p className="muted">Annual volume across the curated MYH dataset.</p>
      </div>
      <div className="chart-frame compact-chart-frame" aria-label="Applications by year chart">
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#edf3f8" strokeDasharray="2 6" vertical={false} />
            <XAxis dataKey="source_year" tickLine={false} axisLine={false} tick={{ fill: "#64748b", fontSize: 11 }} />
            <YAxis tickLine={false} axisLine={false} width={38} tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <Tooltip cursor={{ fill: "rgba(56, 189, 248, 0.08)" }} />
            <Bar dataKey="total_applications" name="Applications" fill="#7c9ccf" barSize={24} radius={[7, 7, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

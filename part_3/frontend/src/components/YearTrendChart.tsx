import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { YearStats } from "../services/api";

interface YearTrendChartProps {
  data: YearStats[];
}

export function YearTrendChart({ data }: YearTrendChartProps) {
  return (
    <article className="chart-card">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Trend</p>
          <h2>Applications by year</h2>
        </div>
        <p className="muted">Total records grouped by source_year.</p>
      </div>
      <div className="chart-frame" aria-label="Applications by year chart">
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={data} margin={{ top: 18, right: 24, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#dbe3ec" strokeDasharray="3 3" />
            <XAxis dataKey="source_year" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="total_applications" name="Applications" fill="#3f6fa8" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

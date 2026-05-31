import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EducationAreaStats, RegionStats } from "@/services/api";

interface CategoryBarsProps {
  regions: RegionStats[];
  educationAreas: EducationAreaStats[];
}

export function CategoryBars({ regions, educationAreas }: CategoryBarsProps) {
  const topRegions = regions.slice(0, 6).map((row) => ({ name: row.lan, applications: row.total_applications }));
  const topEducationAreas = educationAreas.slice(0, 6).map((row) => ({
    name: row.utbildningsomrade,
    applications: row.total_applications,
  }));

  return (
    <section className="chart-grid" aria-label="Category and region charts">
      <article className="chart-card delicate-chart-card">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Region</p>
            <h2>Top län by applications</h2>
          </div>
          <p className="muted">Regional volume in the curated dataset.</p>
        </div>
        <div className="chart-frame compact-chart-frame" aria-label="Top regions chart">
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={topRegions} layout="vertical" margin={{ top: 4, right: 10, left: 16, bottom: 0 }}>
              <CartesianGrid stroke="#edf3f8" strokeDasharray="2 6" horizontal={false} />
              <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <YAxis dataKey="name" type="category" width={112} tickLine={false} axisLine={false} tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="applications" name="Applications" fill="#6ea79d" barSize={13} radius={[0, 7, 7, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </article>

      <article className="chart-card delicate-chart-card">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Education area</p>
            <h2>Top education areas</h2>
          </div>
          <p className="muted">Largest education categories by application volume.</p>
        </div>
        <div className="chart-frame compact-chart-frame" aria-label="Top education areas chart">
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={topEducationAreas} layout="vertical" margin={{ top: 4, right: 10, left: 34, bottom: 0 }}>
              <CartesianGrid stroke="#edf3f8" strokeDasharray="2 6" horizontal={false} />
              <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <YAxis dataKey="name" type="category" width={142} tickLine={false} axisLine={false} tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="applications" name="Applications" fill="#7c9ccf" barSize={13} radius={[0, 7, 7, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </article>
    </section>
  );
}

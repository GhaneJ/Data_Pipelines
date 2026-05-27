import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EducationAreaStats, RegionStats } from "../services/api";

interface CategoryBarsProps {
  regions: RegionStats[];
  educationAreas: EducationAreaStats[];
}

export function CategoryBars({ regions, educationAreas }: CategoryBarsProps) {
  const topRegions = regions.slice(0, 8).map((row) => ({ name: row.lan, applications: row.total_applications }));
  const topEducationAreas = educationAreas.slice(0, 8).map((row) => ({
    name: row.utbildningsomrade,
    applications: row.total_applications,
  }));

  return (
    <section className="chart-grid" aria-label="Category and region charts">
      <article className="chart-card">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Region</p>
            <h2>Top län by applications</h2>
          </div>
          <p className="muted">Uses /stats/by-region.</p>
        </div>
        <div className="chart-frame" aria-label="Top regions chart">
          <ResponsiveContainer width="100%" height={310}>
            <BarChart data={topRegions} layout="vertical" margin={{ top: 8, right: 16, left: 42, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={120} />
              <Tooltip />
              <Bar dataKey="applications" name="Applications" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </article>

      <article className="chart-card">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Education area</p>
            <h2>Top education areas</h2>
          </div>
          <p className="muted">Uses /stats/by-education-area.</p>
        </div>
        <div className="chart-frame" aria-label="Top education areas chart">
          <ResponsiveContainer width="100%" height={310}>
            <BarChart data={topEducationAreas} layout="vertical" margin={{ top: 8, right: 16, left: 80, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={160} />
              <Tooltip />
              <Bar dataKey="applications" name="Applications" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </article>
    </section>
  );
}

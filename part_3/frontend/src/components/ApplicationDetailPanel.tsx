import type { ApiStatus, ApplicationRecord } from "@/services/api";
import { StateMessage } from "@/components/StateMessage";

interface ApplicationDetailPanelProps {
  application: ApplicationRecord | null;
  status: ApiStatus;
  errorMessage: string | null;
}

function renderValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function ApplicationDetailPanel({ application, status, errorMessage }: ApplicationDetailPanelProps) {
  if (!application) {
    return (
      <aside className="detail-card application-profile-card empty-profile-card">
        <div>
          <p className="eyebrow">Application profile</p>
          <h2>Choose a row</h2>
        </div>
        <p className="muted">Choose an education record to open a compact profile card here.</p>
        <StateMessage status={status} errorText={errorMessage} />
      </aside>
    );
  }

  return (
    <aside className="detail-card application-profile-card" aria-labelledby="application-detail-title">
      <div className="application-profile-header">
        <div>
          <p className="eyebrow">Application profile</p>
          <h2 id="application-detail-title">{application.utbildningsnamn}</h2>
          <p className="detail-id">{application.diarienummer}</p>
        </div>
        <span className="compact-pill">{application.beslut_normalized}</span>
      </div>

      <dl className="profile-metric-grid">
        <div><dt>Year</dt><dd>{application.source_year}</dd></div>
        <div><dt>Provider</dt><dd>{application.utbildningsanordnare}</dd></div>
        <div><dt>Region/län</dt><dd>{application.lan}</dd></div>
        <div><dt>Municipality</dt><dd>{application.kommun}</dd></div>
        <div><dt>Municipality / län</dt><dd>{application.kommun} / {application.lan}</dd></div>
        <div><dt>Education area</dt><dd>{application.utbildningsomrade}</dd></div>
        <div><dt>Study form</dt><dd>{application.studieform}</dd></div>
        <div><dt>YH points</dt><dd>{application.yh_poang}</dd></div>
        <div><dt>Study pace</dt><dd>{application.studietakt_procent}%</dd></div>
        <div><dt>Distance based</dt><dd>{renderValue(application.is_distance_based)}</dd></div>
        <div><dt>Approved rounds</dt><dd>{application.beviljade_utbildningsomgangar} of {application.sokta_utbildningsomgangar}</dd></div>
      </dl>
    </aside>
  );
}

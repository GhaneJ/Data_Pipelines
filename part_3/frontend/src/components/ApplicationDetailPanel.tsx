import type { ApiStatus, ApplicationRecord } from "../services/api";
import { StateMessage } from "./StateMessage";

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
      <aside className="detail-card">
        <p className="eyebrow">Detail</p>
        <h2>Select an application</h2>
        <p className="muted">Choose a row in the table to load the public detail endpoint for that diarienummer.</p>
        <StateMessage status={status} errorText={errorMessage} />
      </aside>
    );
  }

  return (
    <aside className="detail-card" aria-labelledby="application-detail-title">
      <p className="eyebrow">Selected application</p>
      <h2 id="application-detail-title">{application.utbildningsnamn}</h2>
      <p className="detail-id">{application.diarienummer}</p>

      <dl className="detail-list">
        <div>
          <dt>Decision</dt>
          <dd>{application.beslut} ({application.beslut_normalized})</dd>
        </div>
        <div>
          <dt>Year</dt>
          <dd>{application.source_year}</dd>
        </div>
        <div>
          <dt>Provider</dt>
          <dd>{application.utbildningsanordnare}</dd>
        </div>
        <div>
          <dt>Education area</dt>
          <dd>{application.utbildningsomrade}</dd>
        </div>
        <div>
          <dt>Municipality / län</dt>
          <dd>{application.kommun} / {application.lan}</dd>
        </div>
        <div>
          <dt>Study form</dt>
          <dd>{application.studieform}</dd>
        </div>
        <div>
          <dt>YH points</dt>
          <dd>{application.yh_poang}</dd>
        </div>
        <div>
          <dt>Study pace</dt>
          <dd>{application.studietakt_procent}%</dd>
        </div>
        <div>
          <dt>Distance based</dt>
          <dd>{renderValue(application.is_distance_based)}</dd>
        </div>
        <div>
          <dt>Approved rounds</dt>
          <dd>{application.beviljade_utbildningsomgangar} of {application.sokta_utbildningsomgangar}</dd>
        </div>
      </dl>
    </aside>
  );
}

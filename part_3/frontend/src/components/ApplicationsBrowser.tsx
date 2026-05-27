import { FormEvent, useEffect, useMemo, useState } from "react";
import { getApplicationByDiarienummer, getApplications } from "../services/api";
import type { ApiStatus, ApplicationFilters, ApplicationList, ApplicationRecord } from "../services/api";
import { ApplicationDetailPanel } from "./ApplicationDetailPanel";
import { StateMessage } from "./StateMessage";

const DEFAULT_FILTERS: ApplicationFilters = {
  source_year: "",
  decision: "",
  region: "",
  municipality: "",
  provider: "",
  education_area: "",
  study_form: "",
  limit: 25,
  offset: 0,
};

function normalizeFilters(filters: ApplicationFilters): ApplicationFilters {
  return {
    ...filters,
    source_year: filters.source_year === "" ? undefined : filters.source_year,
    limit: 25,
    offset: 0,
  };
}

export function ApplicationsBrowser() {
  const [filters, setFilters] = useState<ApplicationFilters>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ApplicationFilters>(normalizeFilters(DEFAULT_FILTERS));
  const [listStatus, setListStatus] = useState<ApiStatus>("idle");
  const [listError, setListError] = useState<string | null>(null);
  const [applicationList, setApplicationList] = useState<ApplicationList | null>(null);
  const [selectedDiarienummer, setSelectedDiarienummer] = useState<string | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<ApplicationRecord | null>(null);
  const [detailStatus, setDetailStatus] = useState<ApiStatus>("idle");
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadApplications() {
      setListStatus("loading");
      setListError(null);
      try {
        const result = await getApplications(appliedFilters);
        if (!isActive) return;
        setApplicationList(result);
        setListStatus("success");
        setSelectedDiarienummer((current) => {
          if (current && result.items.some((item) => item.diarienummer === current)) {
            return current;
          }
          return result.items[0]?.diarienummer ?? null;
        });
      } catch (error) {
        if (!isActive) return;
        setListStatus("error");
        setListError(error instanceof Error ? error.message : "Applications could not be loaded.");
      }
    }

    loadApplications();

    return () => {
      isActive = false;
    };
  }, [appliedFilters]);

  useEffect(() => {
    if (!selectedDiarienummer) {
      setSelectedApplication(null);
      setDetailStatus("idle");
      return;
    }

    let isActive = true;
    const selectedId = selectedDiarienummer;

    async function loadDetail() {
      setDetailStatus("loading");
      setDetailError(null);
      try {
        const result = await getApplicationByDiarienummer(selectedId);
        if (!isActive) return;
        setSelectedApplication(result);
        setDetailStatus("success");
      } catch (error) {
        if (!isActive) return;
        setSelectedApplication(null);
        setDetailStatus("error");
        setDetailError(error instanceof Error ? error.message : "Application detail could not be loaded.");
      }
    }

    loadDetail();

    return () => {
      isActive = false;
    };
  }, [selectedDiarienummer]);

  const rows = applicationList?.items ?? [];
  const totalText = useMemo(() => {
    if (!applicationList) return "No page loaded yet";
    return `${rows.length.toLocaleString("sv-SE")} shown of ${applicationList.total.toLocaleString("sv-SE")} matching applications`;
  }, [applicationList, rows.length]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedFilters(normalizeFilters(filters));
  }

  function handleReset() {
    setFilters(DEFAULT_FILTERS);
    setAppliedFilters(normalizeFilters(DEFAULT_FILTERS));
    setSelectedDiarienummer(null);
  }

  return (
    <section className="dashboard-section" aria-labelledby="applications-browser-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Browse records</p>
          <h2 id="applications-browser-title">Filterable applications</h2>
        </div>
        <p className="muted">A bounded 25-row browser using /applications and /applications/{"{diarienummer}"}.</p>
      </div>

      <div className="browser-layout">
        <article className="browser-card">
          <form className="filters" onSubmit={handleSubmit}>
            <label>
              <span>Year</span>
              <select
                value={filters.source_year ?? ""}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    source_year: event.target.value === "" ? "" : Number(event.target.value),
                  }))
                }
              >
                <option value="">All years</option>
                {[2025, 2024, 2023, 2022, 2021, 2020].map((year) => (
                  <option value={year} key={year}>{year}</option>
                ))}
              </select>
            </label>

            <label>
              <span>Decision</span>
              <select
                value={filters.decision ?? ""}
                onChange={(event) => setFilters((current) => ({ ...current, decision: event.target.value }))}
              >
                <option value="">All decisions</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </label>

            <label>
              <span>Region/län</span>
              <input
                value={filters.region ?? ""}
                placeholder="Stockholm"
                onChange={(event) => setFilters((current) => ({ ...current, region: event.target.value }))}
              />
            </label>

            <label>
              <span>Municipality</span>
              <input
                value={filters.municipality ?? ""}
                placeholder="Göteborg"
                onChange={(event) => setFilters((current) => ({ ...current, municipality: event.target.value }))}
              />
            </label>

            <label>
              <span>Provider</span>
              <input
                value={filters.provider ?? ""}
                placeholder="Yrkeshögskola"
                onChange={(event) => setFilters((current) => ({ ...current, provider: event.target.value }))}
              />
            </label>

            <label>
              <span>Education area</span>
              <input
                value={filters.education_area ?? ""}
                placeholder="Data/IT"
                onChange={(event) => setFilters((current) => ({ ...current, education_area: event.target.value }))}
              />
            </label>

            <label>
              <span>Study form</span>
              <input
                value={filters.study_form ?? ""}
                placeholder="Distans"
                onChange={(event) => setFilters((current) => ({ ...current, study_form: event.target.value }))}
              />
            </label>

            <div className="filter-actions">
              <button type="submit">Apply filters</button>
              <button type="button" className="secondary-button" onClick={handleReset}>Reset</button>
            </div>
          </form>

          <div className="table-meta">
            <strong>{totalText}</strong>
            <span>Limit: 25 rows</span>
          </div>

          <StateMessage
            status={listStatus}
            errorText={listError}
            isEmpty={rows.length === 0}
            emptyText="No applications matched these filters. Try a broader search."
          />

          {listStatus === "success" && rows.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Education</th>
                    <th>Decision</th>
                    <th>Municipality/län</th>
                    <th>Provider</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((application) => (
                    <tr
                      key={application.diarienummer}
                      className={application.diarienummer === selectedDiarienummer ? "selected-row" : undefined}
                      onClick={() => setSelectedDiarienummer(application.diarienummer)}
                    >
                      <td>{application.source_year}</td>
                      <td>
                        <button type="button" className="row-button" onClick={() => setSelectedDiarienummer(application.diarienummer)}>
                          {application.utbildningsnamn}
                        </button>
                        <small>{application.diarienummer}</small>
                      </td>
                      <td>{application.beslut_normalized}</td>
                      <td>{application.kommun} / {application.lan}</td>
                      <td>{application.utbildningsanordnare}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <ApplicationDetailPanel application={selectedApplication} status={detailStatus} errorMessage={detailError} />
      </div>
    </section>
  );
}

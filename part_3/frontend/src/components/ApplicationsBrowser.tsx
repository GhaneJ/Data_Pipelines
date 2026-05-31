import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  getApplicationByDiarienummer,
  getApplications,
  getStatsByEducationArea,
  getStatsByRegion,
  getStatsByYear,
} from "@/services/api";
import type { ApiStatus, ApplicationFilters, ApplicationList, ApplicationRecord } from "@/services/api";
import { searchProviders } from "@/api/providers";
import { ApplicationDetailPanel } from "@/components/ApplicationDetailPanel";
import { StateMessage } from "@/components/StateMessage";
import { SearchableTextSelect } from "@/components/shared/SearchableTextSelect";

const DEFAULT_PAGE_SIZE = 25;
const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;

const DEFAULT_FILTERS: ApplicationFilters = {
  source_year: "",
  decision: "",
  region: "",
  municipality: "",
  provider: "",
  education_area: "",
  study_form: "",
  limit: DEFAULT_PAGE_SIZE,
  offset: 0,
};

interface FilterOptionPool {
  years: string[];
  decisions: string[];
  regions: string[];
  municipalities: string[];
  providers: string[];
  educationAreas: string[];
  studyForms: string[];
}

function normalizeFilters(filters: ApplicationFilters, offset = 0): ApplicationFilters {
  const limit = filters.limit ?? DEFAULT_PAGE_SIZE;

  return {
    ...filters,
    source_year: filters.source_year === "" ? undefined : filters.source_year,
    limit,
    offset,
  };
}

function addOption(target: Set<string>, value: string | null | undefined) {
  const trimmed = value?.trim();
  if (trimmed) target.add(trimmed);
}

function emptyOptionPool(): FilterOptionPool {
  return {
    years: [],
    decisions: ["approved", "rejected", "withdrawn"],
    regions: [],
    municipalities: [],
    providers: [],
    educationAreas: [],
    studyForms: [],
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
  const [optionPool, setOptionPool] = useState<FilterOptionPool>(emptyOptionPool);
  const [providerSearchOptions, setProviderSearchOptions] = useState<string[]>([]);

  useEffect(() => {
    let isActive = true;

    async function loadFilterOptions() {
      try {
        const [yearStats, firstPage, regions, educationAreas] = await Promise.all([
          getStatsByYear(),
          getApplications({ limit: 100, offset: 0 }),
          getStatsByRegion(),
          getStatsByEducationArea(),
        ]);
        if (!isActive) return;

        const years = new Set<string>();
        const decisions = new Set<string>(["approved", "rejected", "withdrawn"]);
        const regionSet = new Set<string>();
        const municipalitySet = new Set<string>();
        const providerSet = new Set<string>();
        const educationSet = new Set<string>();
        const studyFormSet = new Set<string>();

        const collectFromPage = (page: ApplicationList) => {
          page.items.forEach((item) => {
            addOption(years, String(item.source_year));
            addOption(decisions, item.beslut_normalized);
            addOption(regionSet, item.lan);
            addOption(municipalitySet, item.kommun);
            addOption(providerSet, item.utbildningsanordnare);
            addOption(educationSet, item.utbildningsomrade);
            addOption(studyFormSet, item.studieform);
          });
        };

        yearStats.forEach((year) => addOption(years, String(year.source_year)));
        regions.forEach((region) => addOption(regionSet, region.lan));
        educationAreas.forEach((area) => addOption(educationSet, area.utbildningsomrade));
        collectFromPage(firstPage);

        const pageSize = Math.max(firstPage.limit || 100, 1);
        const offsets = Array.from(
          { length: Math.max(0, Math.ceil(firstPage.total / pageSize) - 1) },
          (_, index) => (index + 1) * pageSize,
        );

        const remainingPages = await Promise.all(offsets.map((offset) => getApplications({ limit: pageSize, offset }).catch(() => null)));
        if (!isActive) return;
        remainingPages.forEach((page) => {
          if (page) collectFromPage(page);
        });

        setOptionPool({
          years: Array.from(years).sort((left, right) => Number(right) - Number(left)),
          decisions: Array.from(decisions).sort((left, right) => left.localeCompare(right, "sv-SE")),
          regions: Array.from(regionSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
          municipalities: Array.from(municipalitySet).sort((left, right) => left.localeCompare(right, "sv-SE")),
          providers: Array.from(providerSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
          educationAreas: Array.from(educationSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
          studyForms: Array.from(studyFormSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
        });
      } catch {
        // Filter options are a UX layer. The main list still works without them.
      }
    }

    void loadFilterOptions();
    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;
    const query = (filters.provider ?? "").trim();
    if (query.length < 1) {
      setProviderSearchOptions([]);
      return;
    }

    const timeout = window.setTimeout(async () => {
      try {
        const result = await searchProviders({ q: query, limit: 50 });
        if (!isActive) return;
        setProviderSearchOptions(result.items.map((provider) => provider.utbildningsanordnare));
      } catch {
        if (isActive) setProviderSearchOptions([]);
      }
    }, 180);

    return () => {
      isActive = false;
      window.clearTimeout(timeout);
    };
  }, [filters.provider]);

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
  const currentLimit = appliedFilters.limit ?? DEFAULT_PAGE_SIZE;
  const currentOffset = applicationList?.offset ?? appliedFilters.offset ?? 0;
  const totalApplications = applicationList?.total ?? 0;
  const currentPage = totalApplications === 0 ? 0 : Math.floor(currentOffset / currentLimit) + 1;
  const totalPages = totalApplications === 0 ? 0 : Math.ceil(totalApplications / currentLimit);
  const firstShown = totalApplications === 0 ? 0 : currentOffset + 1;
  const lastShown = applicationList ? Math.min(currentOffset + rows.length, totalApplications) : 0;
  const canGoPrevious = currentOffset > 0 && listStatus !== "loading";
  const canGoNext = currentOffset + currentLimit < totalApplications && listStatus !== "loading";

  const totalText = useMemo(() => {
    if (!applicationList) return "No page loaded yet";
    if (totalApplications === 0) return "No matching applications";
    return `Showing ${firstShown.toLocaleString("sv-SE")}–${lastShown.toLocaleString("sv-SE")} of ${totalApplications.toLocaleString("sv-SE")} applications`;
  }, [applicationList, firstShown, lastShown, totalApplications]);

  const providerOptions = useMemo(() => {
    return Array.from(new Set([...providerSearchOptions, ...optionPool.providers]));
  }, [optionPool.providers, providerSearchOptions]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedFilters(normalizeFilters(filters));
  }

  function handleReset() {
    setFilters(DEFAULT_FILTERS);
    setAppliedFilters(normalizeFilters(DEFAULT_FILTERS));
    setSelectedDiarienummer(null);
  }

  function goToPage(offset: number) {
    const safeOffset = Math.max(0, offset);
    setAppliedFilters((current) => normalizeFilters(current, safeOffset));
  }

  function handleLimitChange(limit: number) {
    const nextFilters = { ...filters, limit };
    setFilters(nextFilters);
    setAppliedFilters(normalizeFilters(nextFilters));
  }

  return (
    <section className="dashboard-section applications-explorer" aria-labelledby="applications-browser-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Historical application records</p>
          <h2 id="applications-browser-title">Applications browser</h2>
        </div>
        <p className="muted">Explore official MYH application records with complete filter choices and a wider table view.</p>
      </div>

      <article className="browser-card refined-browser-card applications-full-width-card">
          <form className="filters smart-filters" onSubmit={handleSubmit}>
            <SearchableTextSelect
              label="Year"
              value={filters.source_year === undefined ? "" : String(filters.source_year)}
              options={optionPool.years}
              placeholder="Search year"
              onChange={(value) => setFilters((current) => ({ ...current, source_year: value === "" ? "" : Number(value) }))}
            />
            <SearchableTextSelect
              label="Decision"
              value={filters.decision ?? ""}
              options={optionPool.decisions}
              placeholder="Search decision"
              onChange={(value) => setFilters((current) => ({ ...current, decision: value }))}
            />
            <SearchableTextSelect
              label="Region/län"
              value={filters.region ?? ""}
              options={optionPool.regions}
              placeholder="Search region"
              onChange={(value) => setFilters((current) => ({ ...current, region: value }))}
            />
            <SearchableTextSelect
              label="Municipality"
              value={filters.municipality ?? ""}
              options={optionPool.municipalities}
              placeholder="Search municipality"
              onChange={(value) => setFilters((current) => ({ ...current, municipality: value }))}
            />
            <SearchableTextSelect
              label="Provider"
              value={filters.provider ?? ""}
              options={providerOptions}
              placeholder="Search provider name"
              helperText="Type letters to search providers by organization name."
              onChange={(value) => setFilters((current) => ({ ...current, provider: value }))}
            />
            <SearchableTextSelect
              label="Education area"
              value={filters.education_area ?? ""}
              options={optionPool.educationAreas}
              placeholder="Search education area"
              onChange={(value) => setFilters((current) => ({ ...current, education_area: value }))}
            />
            <SearchableTextSelect
              label="Study form"
              value={filters.study_form ?? ""}
              options={optionPool.studyForms}
              placeholder="Search study form"
              onChange={(value) => setFilters((current) => ({ ...current, study_form: value }))}
            />

            <div className="filter-actions form-actions-row">
              <button type="submit" className="button primary">Apply filters</button>
              <button type="button" className="button secondary" onClick={handleReset}>Reset</button>
            </div>
          </form>

          <div className="table-meta refined-table-meta">
            <strong>{totalText}</strong>
            <div className="pagination-controls" aria-label="Applications pagination controls">
              <label>
                <span>Rows</span>
                <select
                  value={currentLimit}
                  onChange={(event) => handleLimitChange(Number(event.target.value))}
                  aria-label="Rows per page"
                >
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <option value={size} key={size}>{size}</option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="button secondary compact-button"
                onClick={() => goToPage(currentOffset - currentLimit)}
                disabled={!canGoPrevious}
              >
                Previous
              </button>
              <span className="page-count">
                Page {currentPage.toLocaleString("sv-SE")} of {totalPages.toLocaleString("sv-SE")}
              </span>
              <button
                type="button"
                className="button secondary compact-button"
                onClick={() => goToPage(currentOffset + currentLimit)}
                disabled={!canGoNext}
              >
                Next
              </button>
            </div>
          </div>

          <StateMessage
            status={listStatus}
            errorText={listError}
            isEmpty={rows.length === 0}
            emptyText="No applications matched these filters. Try a broader search."
          />

          <div className="application-profile-slot">
            <ApplicationDetailPanel application={selectedApplication} status={detailStatus} errorMessage={detailError} />
          </div>

          {listStatus === "success" && rows.length > 0 && (
            <div className="table-wrap application-table-wrap">
              <table className="records-table application-records-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Education</th>
                    <th>Decision</th>
                    <th>Region/län</th>
                    <th>Municipality</th>
                    <th>Provider</th>
                    <th>Education area</th>
                    <th>Study form</th>
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
                        <button
                          type="button"
                          className="row-button record-primary"
                          onClick={(event) => { event.stopPropagation(); setSelectedDiarienummer(application.diarienummer); }}
                          aria-label={`Show details for ${application.utbildningsnamn}`}
                        >
                          {application.utbildningsnamn}
                        </button>
                        <small className="record-meta">{application.diarienummer} · View profile card above</small>
                      </td>
                      <td><span className="compact-pill">{application.beslut_normalized}</span></td>
                      <td><span className="record-primary-text">{application.lan}</span></td>
                      <td><span className="record-primary-text">{application.kommun}</span></td>
                      <td><span className="record-primary-text">{application.utbildningsanordnare}</span></td>
                      <td><span className="record-primary-text">{application.utbildningsomrade}</span></td>
                      <td><span className="record-primary-text">{application.studieform}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </article>
    </section>
  );
}

import { FormEvent, useEffect, useMemo, useState } from "react";
import { createProviderSubmission, listProviderSubmissions, submitProviderSubmission, updateProviderSubmission } from "@/api/providerSubmissions";
import type { ProviderSubmission, ProviderSubmissionInput } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";
import { SearchableTextSelect } from "@/components/shared/SearchableTextSelect";
import { getApplications, getStatsByEducationArea, getStatsByRegion, getStatsByYear } from "@/services/api";

const currentYear = new Date().getFullYear();
const optionSamplePageSize = 100;
const optionSamplePageLimit = 8;

const blankSubmission: ProviderSubmissionInput = {
  target_year: currentYear,
  education_name: "",
  education_area: "",
  municipality: "",
  region: "",
  yh_points: 400,
  study_form: "",
  study_pace_percent: 100,
  head_provider_type: "",
  description: "",
  notes: "",
};

interface FormErrors {
  education_name?: string;
  target_year?: string;
  education_area?: string;
  municipality?: string;
  region?: string;
  yh_points?: string;
  study_form?: string;
  study_pace_percent?: string;
}

interface ProviderDraftOptions {
  years: string[];
  educationNames: string[];
  educationAreas: string[];
  municipalities: string[];
  regions: string[];
  studyForms: string[];
  providerTypes: string[];
}

const emptyDraftOptions: ProviderDraftOptions = {
  years: Array.from({ length: 8 }, (_, index) => String(currentYear - 2 + index)),
  educationNames: [],
  educationAreas: [],
  municipalities: [],
  regions: [],
  studyForms: ["Distans", "Bunden", "Flex"],
  providerTypes: ["Privat", "Kommun", "Region", "Stiftelse", "Statlig"],
};

function canEdit(submission: ProviderSubmission) {
  return submission.status === "draft" || submission.status === "needs_changes";
}

function toForm(submission: ProviderSubmission): ProviderSubmissionInput {
  return {
    target_year: submission.target_year,
    education_name: submission.education_name,
    education_area: submission.education_area,
    municipality: submission.municipality,
    region: submission.region,
    yh_points: submission.yh_points,
    study_form: submission.study_form,
    study_pace_percent: submission.study_pace_percent,
    head_provider_type: submission.head_provider_type,
    description: submission.description,
    notes: submission.notes,
  };
}

function addOption(target: Set<string>, value: string | null | undefined) {
  const trimmed = value?.trim();
  if (trimmed) target.add(trimmed);
}

function validateForm(form: ProviderSubmissionInput): FormErrors {
  const errors: FormErrors = {};
  if (!form.education_name.trim()) errors.education_name = "Education name is required.";
  if (!form.education_area?.trim()) errors.education_area = "Choose or type an education area.";
  if (!form.municipality?.trim()) errors.municipality = "Choose or type a municipality.";
  if (!form.region?.trim()) errors.region = "Choose or type a region/län.";
  if (!form.study_form?.trim()) errors.study_form = "Choose or type a study form.";
  const targetYear = Number(form.target_year);
  if (!Number.isInteger(targetYear) || targetYear < 2020 || targetYear > currentYear + 5) errors.target_year = `Target year must be between 2020 and ${currentYear + 5}.`;
  const yhPoints = Number(form.yh_points);
  if (!Number.isFinite(yhPoints) || yhPoints <= 0 || yhPoints > 1000) errors.yh_points = "YH points must be between 1 and 1000.";
  const pace = Number(form.study_pace_percent);
  if (!Number.isInteger(pace) || pace < 1 || pace > 100) errors.study_pace_percent = "Study pace must be between 1 and 100 percent.";
  return errors;
}

function cleanPayload(form: ProviderSubmissionInput): ProviderSubmissionInput {
  return {
    ...form,
    target_year: Number(form.target_year),
    education_name: form.education_name.trim(),
    education_area: form.education_area?.trim() || null,
    municipality: form.municipality?.trim() || null,
    region: form.region?.trim() || null,
    yh_points: Number(form.yh_points),
    study_form: form.study_form?.trim() || null,
    study_pace_percent: Number(form.study_pace_percent),
    head_provider_type: form.head_provider_type?.trim() || null,
    description: form.description?.trim() || null,
    notes: form.notes?.trim() || null,
  };
}

function friendlySubmissionError(error: unknown) {
  if (!(error instanceof Error)) return "The submission could not be saved.";
  if (error.message.includes("Request validation failed")) {
    return "Please review the highlighted fields before saving.";
  }
  if (error.message.includes("not editable") || error.message.includes("transition")) {
    return "This submission cannot be changed in its current status.";
  }
  return error.message;
}

function statusHelp(submission: ProviderSubmission | null) {
  if (!submission) return "Complete the form, save the draft, then send it for admin review.";
  if (submission.status === "draft") return "This draft is editable until you send it for review.";
  if (submission.status === "needs_changes") return "Admin feedback is available. Update the draft and resubmit it.";
  if (submission.status === "submitted") return "This submission has been sent and is waiting for review.";
  if (submission.status === "under_review") return "This submission is being reviewed.";
  if (submission.status === "approved") return "This submission has been approved and is locked.";
  if (submission.status === "rejected") return "This submission has been rejected and is locked.";
  return "Submission status is available in the register.";
}

export function ProviderWorkspacePage() {
  const { user } = useAuth();
  const [items, setItems] = useState<ProviderSubmission[]>([]);
  const [selected, setSelected] = useState<ProviderSubmission | null>(null);
  const [form, setForm] = useState<ProviderSubmissionInput>(blankSubmission);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [formErrorMessage, setFormErrorMessage] = useState<string | null>(null);
  const [draftOptions, setDraftOptions] = useState<ProviderDraftOptions>(emptyDraftOptions);
  const [optionsStatus, setOptionsStatus] = useState<"loading" | "ready" | "partial">("loading");

  async function load() {
    setStatus("loading");
    setError(null);
    try {
      const result = await listProviderSubmissions({ limit: 100 });
      setItems(result.items);
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => { void load(); }, []);

  useEffect(() => {
    let isActive = true;
    async function loadOptions() {
      try {
        const [yearStats, firstPage, regions, educationAreas] = await Promise.all([
          getStatsByYear(),
          getApplications({ limit: optionSamplePageSize, offset: 0 }),
          getStatsByRegion(),
          getStatsByEducationArea(),
        ]);
        if (!isActive) return;

        const yearSet = new Set<string>(emptyDraftOptions.years);
        const educationNameSet = new Set<string>();
        const regionSet = new Set<string>();
        const municipalitySet = new Set<string>();
        const educationSet = new Set<string>();
        const studyFormSet = new Set<string>(emptyDraftOptions.studyForms);
        const providerTypeSet = new Set<string>(emptyDraftOptions.providerTypes);

        const collectFromPage = (page: { items: Array<{ source_year: number; utbildningsnamn: string; lan: string; kommun: string; utbildningsomrade: string; studieform: string; huvudmannatyp: string }> }) => {
          page.items.forEach((item) => {
            addOption(yearSet, String(item.source_year));
            addOption(educationNameSet, item.utbildningsnamn);
            addOption(regionSet, item.lan);
            addOption(municipalitySet, item.kommun);
            addOption(educationSet, item.utbildningsomrade);
            addOption(studyFormSet, item.studieform);
            addOption(providerTypeSet, item.huvudmannatyp);
          });
        };

        const publishOptions = () => {
          setDraftOptions({
            years: Array.from(yearSet).sort((left, right) => Number(right) - Number(left)),
            educationNames: Array.from(educationNameSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
            educationAreas: Array.from(educationSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
            municipalities: Array.from(municipalitySet).sort((left, right) => left.localeCompare(right, "sv-SE")),
            regions: Array.from(regionSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
            studyForms: Array.from(studyFormSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
            providerTypes: Array.from(providerTypeSet).sort((left, right) => left.localeCompare(right, "sv-SE")),
          });
        };

        yearStats.forEach((year) => addOption(yearSet, String(year.source_year)));
        regions.forEach((region) => addOption(regionSet, region.lan));
        educationAreas.forEach((area) => addOption(educationSet, area.utbildningsomrade));
        collectFromPage(firstPage);
        publishOptions();
        setOptionsStatus("partial");

        const pageSize = Math.max(firstPage.limit || optionSamplePageSize, 1);
        const availablePages = Math.max(0, Math.ceil(firstPage.total / pageSize) - 1);
        const pagesToSample = Math.min(availablePages, optionSamplePageLimit - 1);

        for (let pageIndex = 1; pageIndex <= pagesToSample; pageIndex += 1) {
          const page = await getApplications({ limit: pageSize, offset: pageIndex * pageSize }).catch(() => null);
          if (!isActive) return;
          if (page) collectFromPage(page);
          publishOptions();
          await new Promise((resolve) => window.setTimeout(resolve, 0));
        }

        if (isActive) setOptionsStatus("ready");
      } catch {
        if (isActive) setOptionsStatus("partial");
        // Guided choices are helpful but not required for the form to work.
      }
    }
    void loadOptions();
    return () => {
      isActive = false;
    };
  }, []);

  const counts = useMemo(() => ({
    total: items.length,
    draft: items.filter((item) => item.status === "draft").length,
    submitted: items.filter((item) => item.status === "submitted" || item.status === "under_review").length,
    needsChanges: items.filter((item) => item.status === "needs_changes").length,
    final: items.filter((item) => item.status === "approved" || item.status === "rejected").length,
  }), [items]);

  function select(submission: ProviderSubmission) {
    setSelected(submission);
    setForm(toForm(submission));
    setFormErrors({});
    setFormMessage(null);
    setFormErrorMessage(null);
  }

  function startNewDraft() {
    setSelected(null);
    setForm({ ...blankSubmission });
    setFormErrors({});
    setFormMessage(null);
    setFormErrorMessage(null);
  }

  function resetForm() {
    setForm(selected ? toForm(selected) : { ...blankSubmission });
    setFormErrors({});
    setFormMessage(null);
    setFormErrorMessage(null);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setFormMessage(null);
    setFormErrorMessage(null);
    setError(null);
    const errors = validateForm(form);
    setFormErrors(errors);
    if (Object.keys(errors).length > 0) {
      setFormErrorMessage("Please fix the highlighted fields before saving the draft.");
      return;
    }

    try {
      const payload = cleanPayload(form);
      const saved = selected ? await updateProviderSubmission(selected.id, payload) : await createProviderSubmission(payload);
      setSelected(saved);
      setForm(toForm(saved));
      setFormMessage(selected ? "Draft updated successfully." : "Draft created successfully.");
      await load();
    } catch (err) {
      setFormErrorMessage(friendlySubmissionError(err));
    }
  }

  async function submitCurrent() {
    if (!selected) return;
    const errors = validateForm(form);
    setFormErrors(errors);
    if (Object.keys(errors).length > 0) {
      setFormErrorMessage("Please complete the required fields before submitting for review.");
      return;
    }
    try {
      if (canEdit(selected)) {
        await updateProviderSubmission(selected.id, cleanPayload(form));
      }
      const saved = await submitProviderSubmission(selected.id);
      setSelected(saved);
      setForm(toForm(saved));
      setFormMessage("Submission sent for review.");
      await load();
    } catch (err) {
      setFormErrorMessage(friendlySubmissionError(err));
    }
  }

  function updateField<K extends keyof ProviderSubmissionInput>(field: K, value: ProviderSubmissionInput[K]) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: undefined }));
  }

  const editable = !selected || canEdit(selected);
  const providerName = selected?.provider_name || user?.display_name || "Provider account";
  const selectedTitle = selected ? selected.education_name : "Create provider draft";

  return (
    <div className="page-stack provider-workspace-page">
      <section className="hero provider-hero refined-provider-hero">
        <div>
          <p className="eyebrow">Provider workspace</p>
          <h2>{providerName}</h2>
          <p>Create drafts, send them for review, correct records when feedback arrives, and track each decision from one workspace.</p>
          <div className="hero-chip-row">
            <span className="status-pill ok">Signed in as {user?.display_name || user?.username}</span>
            <span className="status-pill neutral">Provider workspace</span>
            <span className="status-pill neutral">Guided choices {optionsStatus === "loading" ? "loading" : "ready"}</span>
          </div>
        </div>
        <div className="mini-metric-grid provider-metrics">
          <article><span>Total</span><strong>{counts.total}</strong></article>
          <article><span>Drafts</span><strong>{counts.draft}</strong></article>
          <article><span>In review</span><strong>{counts.submitted}</strong></article>
          <article><span>Needs changes</span><strong>{counts.needsChanges}</strong></article>
        </div>
      </section>

      <div className="split-grid provider-work-grid refined-provider-grid">
        <section className="panel table-panel provider-list-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Submission register</p>
              <h2>My submissions</h2>
            </div>
            <button className="button primary" type="button" onClick={startNewDraft}>New draft</button>
          </div>
          <div className="provider-context-card refined-context-card">
            <strong>{user?.display_name || "Provider account"}</strong>
            <span>{user?.username} · Provider</span>
            <small>Drafts, submitted records, feedback, and final decisions are shown here.</small>
          </div>
          {error !== null && <ErrorPanel error={error} />}
          {status === "loading" && <LoadingState text="Loading provider submissions..." />}
          {status === "success" && items.length === 0 && <EmptyState title="No submissions yet" text="Create a draft to start your first review workflow." />}
          {status === "success" && items.length > 0 && (
            <table className="records-table provider-submissions-table refined-provider-table">
              <thead><tr><th>Submission</th><th>Status</th><th>Feedback</th><th>Updated</th><th>Action</th></tr></thead>
              <tbody>{items.map((item) => (
                <tr key={item.id} className={selected?.id === item.id ? "selected-row" : ""} onClick={() => select(item)}>
                  <td>
                    <strong>{item.education_name}</strong>
                    <span>{item.target_year ?? "—"} · {item.municipality ?? "—"} · {item.region ?? "—"}</span>
                  </td>
                  <td><StatusBadge status={item.status} /></td>
                  <td>{item.review_notes ?? "—"}</td>
                  <td>{new Date(item.updated_at).toLocaleString("sv-SE")}</td>
                  <td><button type="button" className="button secondary compact-button" onClick={(event) => { event.stopPropagation(); select(item); }}>{canEdit(item) ? "Open / edit" : "Open"}</button></td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </section>

        <section className="panel provider-form-panel refined-provider-form-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{selected ? "Selected submission" : "New submission"}</p>
              <h2>{selectedTitle}</h2>
              <p className="muted">{statusHelp(selected)}</p>
            </div>
            {selected && <StatusBadge status={selected.status} />}
          </div>

          {selected && !editable && <div className="alert alert-info compact-alert">This submission is locked in its current status.</div>}
          {selected?.status === "needs_changes" && <div className="alert alert-warning"><strong>Review feedback:</strong> {selected.review_notes ?? "Changes requested."}</div>}
          {formMessage && <div className="alert alert-success compact-alert">{formMessage}</div>}
          {formErrorMessage && <div className="alert alert-error compact-alert" role="alert"><strong>{formErrorMessage}</strong></div>}

          <form className="provider-submission-form refined-submission-form" onSubmit={save} noValidate>
            <SearchableTextSelect
              label="Education name"
              value={form.education_name}
              options={draftOptions.educationNames}
              placeholder="Search or type education name"
              onChange={(value) => updateField("education_name", value)}
              disabled={!editable}
              errorText={formErrors.education_name}
              className="wide"
            />
            <SearchableTextSelect
              label="Target year"
              value={form.target_year === undefined || form.target_year === null ? "" : String(form.target_year)}
              options={draftOptions.years}
              placeholder="Search target year"
              onChange={(value) => {
                const numericYear = Number(value);
                updateField("target_year", value === "" || !Number.isFinite(numericYear) ? null : numericYear);
              }}
              emptyLabel="Clear target year"
              disabled={!editable}
              errorText={formErrors.target_year}
            />
            <label className="field">YH points
              <input className={formErrors.yh_points ? "field-invalid" : ""} type="number" value={form.yh_points ?? ""} disabled={!editable} onChange={(event) => updateField("yh_points", Number(event.target.value))} />
              {formErrors.yh_points && <small className="field-error">{formErrors.yh_points}</small>}
            </label>
            <SearchableTextSelect
              label="Education area"
              value={form.education_area ?? ""}
              options={draftOptions.educationAreas}
              placeholder="Search education area"
              onChange={(value) => updateField("education_area", value)}
              disabled={!editable}
              errorText={formErrors.education_area}
            />
            <SearchableTextSelect
              label="Municipality"
              value={form.municipality ?? ""}
              options={draftOptions.municipalities}
              placeholder="Search municipality"
              onChange={(value) => updateField("municipality", value)}
              disabled={!editable}
              errorText={formErrors.municipality}
            />
            <SearchableTextSelect
              label="Region/län"
              value={form.region ?? ""}
              options={draftOptions.regions}
              placeholder="Search region"
              onChange={(value) => updateField("region", value)}
              disabled={!editable}
              errorText={formErrors.region}
            />
            <SearchableTextSelect
              label="Study form"
              value={form.study_form ?? ""}
              options={draftOptions.studyForms}
              placeholder="Search study form"
              onChange={(value) => updateField("study_form", value)}
              disabled={!editable}
              errorText={formErrors.study_form}
            />
            <label className="field">Study pace %
              <input className={formErrors.study_pace_percent ? "field-invalid" : ""} type="number" value={form.study_pace_percent ?? ""} disabled={!editable} onChange={(event) => updateField("study_pace_percent", Number(event.target.value))} />
              {formErrors.study_pace_percent && <small className="field-error">{formErrors.study_pace_percent}</small>}
            </label>
            <SearchableTextSelect
              label="Provider type"
              value={form.head_provider_type ?? ""}
              options={draftOptions.providerTypes}
              placeholder="Search provider type"
              onChange={(value) => updateField("head_provider_type", value)}
              disabled={!editable}
            />
            <label className="field wide">Description
              <textarea value={form.description ?? ""} disabled={!editable} onChange={(event) => updateField("description", event.target.value)} />
            </label>
            <label className="field wide">Provider notes
              <textarea value={form.notes ?? ""} disabled={!editable} onChange={(event) => updateField("notes", event.target.value)} />
            </label>
            <div className="actions action-cluster spacious-actions provider-form-actions">
              {editable && <button className="button primary" type="submit">{selected ? "Save draft changes" : "Create draft"}</button>}
              {editable && <button className="button secondary" type="button" onClick={resetForm}>Reset form</button>}
              {selected && editable && <ConfirmButton className="button primary" confirmText="Submit this record for admin review?" onConfirm={submitCurrent}>{selected.status === "needs_changes" ? "Resubmit for review" : "Submit for review"}</ConfirmButton>}
              {selected && <button className="button secondary" type="button" onClick={startNewDraft}>Start new draft</button>}
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}

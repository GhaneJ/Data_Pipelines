import { FormEvent, useEffect, useState } from "react";
import { createProviderSubmission, listProviderSubmissions, submitProviderSubmission, updateProviderSubmission } from "@/api/providerSubmissions";
import type { ProviderSubmission, ProviderSubmissionInput } from "@/api/types";
import { StatusBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";
import { useAuth } from "@/auth/AuthContext";

const blankSubmission: ProviderSubmissionInput = {
  target_year: new Date().getFullYear(),
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

function canEdit(submission: ProviderSubmission) {
  return submission.status === "draft" || submission.status === "needs_changes";
}

export function ProviderWorkspacePage() {
  const { user } = useAuth();
  const [items, setItems] = useState<ProviderSubmission[]>([]);
  const [selected, setSelected] = useState<ProviderSubmission | null>(null);
  const [form, setForm] = useState<ProviderSubmissionInput>(blankSubmission);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);

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

  function select(submission: ProviderSubmission) {
    setSelected(submission);
    setForm({
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
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const payload = { ...form, target_year: Number(form.target_year), yh_points: Number(form.yh_points), study_pace_percent: Number(form.study_pace_percent) };
      const saved = selected ? await updateProviderSubmission(selected.id, payload) : await createProviderSubmission(payload);
      setSelected(saved);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function submitCurrent() {
    if (!selected) return;
    try {
      const saved = await submitProviderSubmission(selected.id);
      setSelected(saved);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  const editable = !selected || canEdit(selected);

  return (
    <div className="split-grid">
      <section className="panel table-panel">
        <div className="section-heading"><div><p className="eyebrow">Provider workspace</p><h2>My submissions</h2></div><button className="button primary" type="button" onClick={() => { setSelected(null); setForm(blankSubmission); }}>New draft</button></div>
        <p className="muted">Logged in as provider {user?.provider_id}. Only your own provider submissions are loaded by the backend.</p>
        {error !== null && <ErrorPanel error={error} />}
        {status === "loading" && <LoadingState text="Loading provider submissions..." />}
        {status === "success" && items.length === 0 && <EmptyState title="No submissions" text="Create a draft to start the provider workflow." />}
        {items.length > 0 && <table><thead><tr><th>Education</th><th>Status</th><th>Feedback</th><th>Updated</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className={selected?.id === item.id ? "selected-row" : ""} onClick={() => select(item)}><td><strong>{item.education_name}</strong><span>{item.municipality ?? "—"} · {item.region ?? "—"}</span></td><td><StatusBadge status={item.status} /></td><td>{item.review_notes ?? "—"}</td><td>{new Date(item.updated_at).toLocaleString()}</td></tr>)}</tbody></table>}
      </section>
      <section className="panel">
        <div className="section-heading"><div><p className="eyebrow">Draft and correction form</p><h2>{selected ? selected.education_name : "New provider submission"}</h2></div>{selected && <StatusBadge status={selected.status} />}</div>
        {selected && !editable && <div className="alert alert-info">Editing is blocked while this submission is {selected.status}. The backend also enforces this workflow rule.</div>}
        {selected?.status === "needs_changes" && <div className="alert alert-warning"><strong>Admin feedback:</strong> {selected.review_notes ?? "Changes requested."}</div>}
        <form className="form-grid single" onSubmit={save}>
          <label>Education name<input value={form.education_name} required disabled={!editable} onChange={(event) => setForm({ ...form, education_name: event.target.value })} /></label>
          <label>Target year<input type="number" value={form.target_year ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, target_year: Number(event.target.value) })} /></label>
          <label>Education area<input value={form.education_area ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, education_area: event.target.value })} /></label>
          <label>Municipality<input value={form.municipality ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, municipality: event.target.value })} /></label>
          <label>Region<input value={form.region ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, region: event.target.value })} /></label>
          <label>YH points<input type="number" value={form.yh_points ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, yh_points: Number(event.target.value) })} /></label>
          <label>Study form<input value={form.study_form ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, study_form: event.target.value })} /></label>
          <label>Study pace %<input type="number" value={form.study_pace_percent ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, study_pace_percent: Number(event.target.value) })} /></label>
          <label className="wide">Description<textarea value={form.description ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <label className="wide">Provider notes<textarea value={form.notes ?? ""} disabled={!editable} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
          {editable && <button className="button primary" type="submit">{selected ? "Save changes" : "Create draft"}</button>}
          {selected && editable && <ConfirmButton className="button primary" confirmText="Submit this record for admin review?" onConfirm={submitCurrent}>{selected.status === "needs_changes" ? "Resubmit" : "Submit for review"}</ConfirmButton>}
        </form>
      </section>
    </div>
  );
}

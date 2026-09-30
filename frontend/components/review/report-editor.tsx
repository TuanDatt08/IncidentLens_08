"use client";

import { useEffect, useState } from "react";
import { Info, Lock, Save } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { getIncidentReport, isEditableReviewState, ReportConflictError, updateReport } from "@/services/report.service";
import type { IncidentDraft } from "@/types/incident";
import type { ReportPatch } from "@/types/report";

type EditorValues = {
  summary: string;
  observations: string;
  key_factors: string;
  unknowns: string;
};

function toEditorValues(draft: IncidentDraft): EditorValues {
  return {
    summary: draft.summary ?? "",
    observations: draft.observations.map(formatItem).join("\n"),
    key_factors: draft.key_factors.map(formatItem).join("\n"),
    unknowns: draft.unknowns.map(formatItem).join("\n"),
  };
}

function formatItem(item: unknown): string {
  return typeof item === "string" ? item : JSON.stringify(item) ?? String(item);
}

function toList(value: string): string[] {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

export function ReportEditor({ id, draft, onSaved }: { id: string; draft: IncidentDraft; onSaved: (draft: IncidentDraft) => void }) {
  const [values, setValues] = useState<EditorValues>(() => toEditorValues(draft));
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [hasConflict, setHasConflict] = useState(false);
  const editable = isEditableReviewState(draft.review_status);

  useEffect(() => {
    setValues(toEditorValues(draft));
  }, [draft]);

  useEffect(() => {
    setHasConflict(false);
    setError("");
    setMessage("");
  }, [id]);

  function update(field: keyof EditorValues, value: string) {
    setMessage("");
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    if (!editable) return;
    const current = toEditorValues(draft);
    const patch: ReportPatch = { version: draft.version };
    if (values.summary !== current.summary) patch.summary = values.summary;
    if (values.observations !== current.observations) patch.observations = toList(values.observations);
    if (values.key_factors !== current.key_factors) patch.key_factors = toList(values.key_factors);
    if (values.unknowns !== current.unknowns) patch.unknowns = toList(values.unknowns);
    if (Object.keys(patch).length === 1) {
      setMessage("No changes to save.");
      return;
    }
    setIsSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await updateReport(id, patch);
      onSaved(updated);
      setHasConflict(false);
      setMessage("Changes saved.");
    } catch (reason) {
      if (reason instanceof ReportConflictError) {
        setHasConflict(true);
        setError(`${reason.message}${reason.currentVersion !== undefined ? ` Current version: ${reason.currentVersion}.` : ""} Reload the latest report before saving. Reloading will discard unsaved edits.`);
      } else {
        setError(reason instanceof Error ? reason.message : "Changes could not be saved.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  async function reloadLatest() {
    setIsSaving(true);
    try {
      const latest = await getIncidentReport(id);
      onSaved(latest);
      setHasConflict(false);
      setError("");
      setMessage("Latest report loaded.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The latest report could not be loaded.");
    } finally {
      setIsSaving(false);
    }
  }

  return <section className="section-card p-5 sm:p-6"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><p className="eyebrow">Engineer workspace</p><h2 className="mt-2 text-xl font-extrabold tracking-[-0.03em] text-vf-navy">Editable Incident Report</h2><p className="mt-1 text-xs font-semibold text-slate-400">Review and refine the AI draft before submitting it.</p></div>{!editable && <span className="inline-flex items-center gap-1.5 self-start rounded-full bg-slate-100 px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.08em] text-slate-500"><Lock className="h-3 w-3" /> Read-only</span>}</div>{draft.review_status === "REJECTED" && draft.rejection_reason && <div className="mt-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3"><p className="text-[10px] font-extrabold uppercase tracking-[0.1em] text-red-600">Rejection feedback</p><p className="mt-1 text-xs font-semibold leading-5 text-red-800">{draft.rejection_reason}</p></div>}<div className="mt-6 space-y-5"><div><label htmlFor="summary" className="field-label">Summary text</label><textarea id="summary" disabled={!editable} value={values.summary} onChange={(event) => update("summary", event.target.value)} rows={4} className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm font-semibold leading-6 text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500" /></div><div className="grid gap-5 lg:grid-cols-3"><ListField id="observations" label="Observations" hint="One item per line" value={values.observations} disabled={!editable} onChange={(value) => update("observations", value)} /><ListField id="key-factors" label="Key factors" hint="One item per line" value={values.key_factors} disabled={!editable} onChange={(value) => update("key_factors", value)} /><ListField id="unknowns" label="Unknowns" hint="One item per line" value={values.unknowns} disabled={!editable} onChange={(value) => update("unknowns", value)} /></div><div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4"><div className="flex items-center gap-2 text-xs font-extrabold text-slate-600"><Info className="h-4 w-4 text-vf-primary" /> AI-generated context</div><p className="mt-2 text-xs font-semibold leading-5 text-slate-500">Incident type and incident window are read-only in this MVP.</p></div></div>{error && <p className="mt-4 text-xs font-bold text-red-600">{error}</p>}<div className="mt-6 flex flex-col items-start justify-between gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center"><span className={`text-xs font-bold ${error ? "text-red-600" : "text-emerald-600"}`}>{message}</span>{editable && (hasConflict ? <Button variant="ghost" onClick={reloadLatest} disabled={isSaving}>Reload latest report</Button> : <Button onClick={save} disabled={isSaving}><Save className="h-4 w-4" />{isSaving ? "Saving…" : "Save Changes"}</Button>)}</div></section>;
}

function ListField({ id, label, hint, value, disabled, onChange }: { id: string; label: string; hint: string; value: string; disabled: boolean; onChange: (value: string) => void }) {
  return <div><div className="mb-2 flex items-center justify-between"><label htmlFor={id} className="field-label mb-0">{label}</label><span className="text-[10px] font-bold text-slate-400">{hint}</span></div><textarea id={id} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} rows={5} className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-xs font-semibold leading-5 text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500" /></div>;
}

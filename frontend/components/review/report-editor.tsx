"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Lock, Save } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { clearDraftRecovery, readDraftRecovery, writeDraftRecovery } from "@/lib/draft-recovery";
import { useUnsavedChanges } from "@/lib/use-unsaved-changes";
import { parseEditorItems } from "@/lib/report-editor-values";
import { getIncidentReport, isEditableReviewState, ReportConflictError, updateReport } from "@/services/report.service";
import type { IncidentDraft } from "@/types/incident";
import type { ReportPatch } from "@/types/report";

type EditorValues = {
  summary: string;
  observations: string;
  key_factors: string;
  unknowns: string;
};

function isEditorValues(value: unknown): value is EditorValues {
  if (!value || typeof value !== "object") return false;
  return ["summary", "observations", "key_factors", "unknowns"].every((field) => field in value && typeof (value as Record<string, unknown>)[field] === "string");
}

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

export type EditorState = { dirty: boolean; saving: boolean };

export function ReportEditor({ id, draft, onSaved, onStateChange }: { id: string; draft: IncidentDraft; onSaved: (draft: IncidentDraft) => void; onStateChange: (state: EditorState) => void }) {
  const { user, can } = useAuth();
  const [values, setValues] = useState<EditorValues>(() => toEditorValues(draft));
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [hasConflict, setHasConflict] = useState(false);
  const [recoveryReady, setRecoveryReady] = useState(false);
  const [baseVersion, setBaseVersion] = useState(draft.version);
  const [staleRecovery, setStaleRecovery] = useState<{ version: number; value: EditorValues } | null>(null);
  const [recoveryWarning, setRecoveryWarning] = useState("");
  const recoveryKey = `v1:${user?.id}:${id}`;
  const editable = can("report:edit") && isEditableReviewState(draft.review_status);
  const requestInFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const hydratedDraft = useRef<{ key: string; draft: IncidentDraft }>();
  const currentValues = toEditorValues(draft);
  const dirty = !!staleRecovery || baseVersion !== draft.version || Object.keys(values).some((field) => values[field as keyof EditorValues] !== currentValues[field as keyof EditorValues]);
  useUnsavedChanges(dirty, isSaving);

  useEffect(() => {
    onStateChange({ dirty: !recoveryReady || dirty, saving: isSaving });
  }, [dirty, isSaving, onStateChange, recoveryReady]);

  useEffect(() => {
    if (hydratedDraft.current?.key === recoveryKey && hydratedDraft.current.draft === draft) return;
    const firstLoad = hydratedDraft.current?.key !== recoveryKey;
    hydratedDraft.current = { key: recoveryKey, draft };
    if (!firstLoad) {
      setBaseVersion(draft.version);
      setValues(toEditorValues(draft));
      return;
    }
    const recovery = readDraftRecovery(recoveryKey, isEditorValues);
    setRecoveryReady(true);
    setBaseVersion(draft.version);
    setStaleRecovery(recovery && (recovery.version !== draft.version || !isEditableReviewState(draft.review_status)) ? recovery : null);
    setValues(recovery && recovery.version === draft.version && isEditableReviewState(draft.review_status) ? recovery.value : toEditorValues(draft));
    setMessage(recovery && recovery.version === draft.version && isEditableReviewState(draft.review_status) ? "Unsaved edits restored from this tab." : "");
  }, [draft, recoveryKey]);

  useEffect(() => {
    setHasConflict(false);
    setError("");
  }, [id]);

  function update(field: keyof EditorValues, value: string) {
    if (requestInFlight.current || !editable || staleRecovery) return;
    setMessage("");
    const next = { ...values, [field]: value };
    setValues(next);
    const matchesServer = baseVersion === draft.version && Object.keys(next).every((key) => next[key as keyof EditorValues] === currentValues[key as keyof EditorValues]);
    const retained = matchesServer ? clearDraftRecovery(recoveryKey) : writeDraftRecovery(recoveryKey, baseVersion, next);
    setRecoveryWarning(retained ? "" : matchesServer ? "Your edits match the report, but this tab could not remove its recovery copy." : "This tab could not retain a recovery copy. Save your edits before leaving.");
  }

  async function save() {
    if (!editable || requestInFlight.current || hasConflict || staleRecovery) return;
    const current = toEditorValues(draft);
    const patch: ReportPatch = { version: baseVersion };
    if (values.summary !== current.summary) patch.summary = values.summary;
    try {
      if (values.observations !== current.observations) patch.observations = parseEditorItems(values.observations, draft.observations);
      if (values.key_factors !== current.key_factors) patch.key_factors = parseEditorItems(values.key_factors, draft.key_factors);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Evidence items are invalid.");
      return;
    }
    if (values.unknowns !== current.unknowns) patch.unknowns = toList(values.unknowns);
    if (Object.keys(patch).length === 1 && baseVersion === draft.version) {
      setMessage("No changes to save.");
      return;
    }
    requestInFlight.current = true;
    setIsSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await updateReport(id, patch);
      if (!mounted.current) return;
      const removed = clearDraftRecovery(recoveryKey);
      if (removed) setStaleRecovery(null);
      setRecoveryWarning(removed ? "" : "The report loaded successfully, but this tab could not remove its recovery copy.");
      onSaved(updated);
      setHasConflict(false);

      setMessage("Changes saved.");
    } catch (reason) {
      if (!mounted.current) return;
      if (reason instanceof ReportConflictError) {
        setHasConflict(true);
        setError(`${reason.message}${reason.currentVersion !== undefined ? ` Current version: ${reason.currentVersion}.` : ""} Reload the latest report before saving. Reloading will discard unsaved edits.`);
      } else {
        setError(reason instanceof Error ? reason.message : "Changes could not be saved.");
      }
    } finally {
      if (mounted.current) {
        requestInFlight.current = false;
        setIsSaving(false);
      }
    }
  }

  async function reloadLatest() {
    if (requestInFlight.current) return;
    if ((dirty || staleRecovery) && !window.confirm("Discard the recovered or unsaved edits and load the latest report?")) return;
    requestInFlight.current = true;
    setIsSaving(true);
    try {
      const latest = await getIncidentReport(id);
      if (!mounted.current) return;
      const removed = clearDraftRecovery(recoveryKey);
      if (removed) setStaleRecovery(null);
      setRecoveryWarning(removed ? "" : "The latest report loaded, but this tab could not remove its recovery copy.");
      onSaved(latest);
      setHasConflict(false);
      setError("");
      setMessage("Latest report loaded.");
    } catch (reason) {
      if (!mounted.current) return;
      setError(reason instanceof Error ? reason.message : "The latest report could not be loaded.");
    } finally {
      if (mounted.current) {
        requestInFlight.current = false;
        setIsSaving(false);
      }
    }
  }

  function restoreOldEdits() {
    if (!staleRecovery || requestInFlight.current) return;
    setValues(staleRecovery.value);
    setBaseVersion(staleRecovery.version);
    setStaleRecovery(null);
    setHasConflict(false);
    setMessage("Older edits restored for copying. Saving requires a version check; copy the fields you need before reloading the latest report.");
  }

  function discardRecovery() {
    if (requestInFlight.current) return;
    if (!window.confirm("Discard this tab’s recovered edits?")) return;
    if (!clearDraftRecovery(recoveryKey)) {
      setRecoveryWarning("This tab could not remove its recovery copy. Your recovered edits have been kept.");
      return;
    }
    setStaleRecovery(null);
    setRecoveryWarning("");
  }

  return <section className="section-card report-editor-surface p-5 sm:p-6"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><h2 className="text-lg font-semibold text-vf-navy">01 / Bản nháp báo cáo</h2></div>{!editable && <span className="inline-flex items-center gap-1.5 self-start rounded-full bg-slate-100 px-2.5 py-1.5 text-[10px] font-semibold  text-slate-500"><Lock className="h-3 w-3" /> Read-only</span>}</div>{draft.review_status === "REJECTED" && draft.rejection_reason && <div className="mt-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3"><p className="text-[10px] font-semibold  text-red-600">Rejection feedback</p><p className="mt-1 text-xs font-semibold leading-5 text-red-800">{draft.rejection_reason}</p></div>}{staleRecovery && <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4"><p role="status" className="text-sm font-semibold text-amber-900">This tab has unsaved edits from version {staleRecovery.version}. The latest report is version {draft.version}. {editable ? "Restore them to copy your text, or discard the recovery copy." : "This report is read-only. Your recovered text is shown separately below for copying."}</p>{!editable && <div className="mt-3 space-y-3">{Object.entries(staleRecovery.value).map(([field, text]) => <label key={field} className="block text-sm font-semibold">Recovered {field.replaceAll("_", " ")}<textarea readOnly value={text} rows={3} className="mt-1 w-full rounded-lg border border-amber-200 bg-white p-3 text-sm" /></label>)}</div>}<div className="mt-3 flex flex-wrap gap-2"><Button variant="ghost" disabled={isSaving || !editable} onClick={restoreOldEdits}>Restore old edits</Button><Button variant="ghost" disabled={isSaving} onClick={discardRecovery}>Discard recovered edits</Button></div></div>}{recoveryWarning && <p role="status" className="mt-4 text-sm font-semibold text-amber-800">{recoveryWarning}</p>}<div className="mt-6 space-y-5"><div><label htmlFor="summary" className="field-label">Tóm tắt sự cố</label><textarea id="summary" disabled={!editable || isSaving || !!staleRecovery} value={values.summary} onChange={(event) => update("summary", event.target.value)} rows={4} className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm font-semibold leading-6 text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500" /></div><div className="grid gap-4"><ListField id="observations" label="Quan sát từ dữ liệu" hint="One item per line" value={values.observations} disabled={!editable || isSaving || !!staleRecovery} onChange={(value) => update("observations", value)} /><ListField id="key-factors" label="Yếu tố quan trọng" hint="One item per line" value={values.key_factors} disabled={!editable || isSaving || !!staleRecovery} onChange={(value) => update("key_factors", value)} /><ListField id="unknowns" label="Giới hạn & điểm chưa xác định" hint="One item per line" value={values.unknowns} disabled={!editable || isSaving || !!staleRecovery} onChange={(value) => update("unknowns", value)} /></div></div>{error && <p role="alert" className="mt-4 text-xs font-bold text-red-600">{error}</p>}<div className="mt-6 flex flex-col items-start justify-between gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center"><span role="status" className={`text-xs font-bold ${error ? "text-red-600" : "text-emerald-600"}`}>{message}</span>{editable && (hasConflict ? <Button variant="ghost" onClick={reloadLatest} disabled={isSaving}>Reload latest report</Button> : <Button onClick={save} disabled={isSaving || !!staleRecovery}><Save className="h-4 w-4" />{isSaving ? "Saving…" : "Save Changes"}</Button>)}{editable && baseVersion !== draft.version && !hasConflict && <Button variant="ghost" onClick={reloadLatest} disabled={isSaving}>Reload latest report</Button>}</div></section>;
}

function ListField({ id, label, hint, value, disabled, onChange }: { id: string; label: string; hint: string; value: string; disabled: boolean; onChange: (value: string) => void }) {
  return <div><div className="mb-2 flex flex-wrap items-center justify-between gap-x-2 gap-y-1"><label htmlFor={id} className="field-label mb-0">{label}</label><span className="text-[10px] font-bold text-slate-400">{hint}</span></div><textarea id={id} readOnly={disabled} value={value} onChange={(event) => onChange(event.target.value)} rows={5} className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-xs font-semibold leading-5 text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary read-only:cursor-default read-only:bg-slate-50 read-only:text-slate-500" /></div>;
}

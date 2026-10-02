"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { AuditSection } from "./audit-section";
import { V2_BASE_URL, v2Error, v2Request } from "@/services/v2.service";
import type { AnalysisV2, AuditV2, EvidenceV2, PageV2, ReportV2, SessionV2 } from "@/types/v2";

type Decision = "submit" | "approve" | "reject" | "reopen";

export function ReportWorkspaceV2({ id }: { id: string }) {
  const [report, setReport] = useState<ReportV2>();
  const [draft, setDraft] = useState<AnalysisV2>();
  const [session, setSession] = useState<SessionV2>();
  const [evidence, setEvidence] = useState<EvidenceV2[]>([]);
  const [audit, setAudit] = useState<AuditV2[]>([]);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditError, setAuditError] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [decision, setDecision] = useState<Decision>();
  const [reason, setReason] = useState("");
  const [mediaError, setMediaError] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  const loadAudit = useCallback(async () => {
    setAuditLoading(true); setAuditError("");
    try { setAudit((await v2Request<PageV2<AuditV2>>(`/reports/${id}/audit`)).items); }
    catch (cause) { setAuditError(v2Error(cause)); }
    finally { setAuditLoading(false); }
  }, [id]);
  const load = useCallback(async () => {
    setError("");
    try {
      const [data, assets, identity] = await Promise.all([v2Request<ReportV2>(`/reports/${id}`), v2Request<PageV2<EvidenceV2>>(`/reports/${id}/evidence`), v2Request<SessionV2>("/session")]);
      setReport(data); setDraft(structuredClone(data.analysis)); setEvidence(assets.items); setSession(identity);
    } catch (cause) { setError(v2Error(cause)); }
    await loadAudit();
  }, [id, loadAudit]);
  useEffect(() => { void load(); }, [load]);
  const editable = report?.analysis.review_status === "DRAFT" && session?.roles.includes("Engineer");
  const dirty = report && draft && JSON.stringify(report.analysis) !== JSON.stringify(draft);
  async function save() {
    if (!report || !draft) return;
    setWorking(true); setError("");
    try {
      const updated = await v2Request<ReportV2>(`/reports/${id}`, { method: "PATCH", body: JSON.stringify({ expected_version: report.version, summary: draft.summary, timeline: draft.timeline, factors: draft.factors, unknowns: draft.unknowns }) });
      setReport(updated); setDraft(structuredClone(updated.analysis)); await loadAudit();
    } catch (cause) { setError(v2Error(cause)); }
    finally { setWorking(false); }
  }
  async function transition() {
    if (!report || !decision) return;
    setWorking(true); setError("");
    try {
      const updated = await v2Request<ReportV2>(`/reports/${id}/${decision}`, { method: "POST", body: JSON.stringify({ expected_version: report.version, ...(decision === "reject" ? { reason } : {}) }) });
      setReport(updated); setDraft(structuredClone(updated.analysis)); setDecision(undefined); setReason(""); await loadAudit();
    } catch (cause) { setError(v2Error(cause)); }
    finally { setWorking(false); }
  }
  const clip = evidence.find((asset) => asset.media_type === "video/mp4" && asset.media_url);
  function seek(time_s: number) {
    if (!clip || !video.current) return;
    const relative = time_s - clip.start_s;
    if (relative >= 0 && relative <= clip.end_s - clip.start_s) video.current.currentTime = relative;
  }
  return <div className="mx-auto max-w-5xl space-y-6">
    <div className="flex flex-wrap justify-between gap-3"><h1 className="break-words text-3xl font-bold text-vf-navy">Report review</h1><Button variant="ghost" onClick={() => { if (!dirty || window.confirm("Discard unsaved edits and load the latest report?")) void load(); }} disabled={working}>Reload latest report</Button></div>
    {!report && !error && <p role="status">Loading report and evidence…</p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {report && draft && <>
      <Link href={`/recordings/${encodeURIComponent(report.recording_id)}`} className="font-semibold text-vf-primary underline underline-offset-4">Back to recording</Link>
      <p className="text-sm text-slate-700">{draft.review_status} · Version {report.version} · {draft.event_type}</p>
      <section className="section-card space-y-4 p-5 sm:p-6"><h2 className="text-xl font-bold text-vf-navy">Evidence</h2>
        {clip?.media_url ? <video ref={video} aria-label="Approved masked incident clip" src={V2_BASE_URL + clip.media_url} controls preload="metadata" onError={() => setMediaError("Evidence media could not be loaded. Refresh or ask an Engineer to check its privacy state.")} className="aspect-video w-full rounded-lg bg-vf-navy" /> : <p className="text-sm text-slate-600">Video playback is unavailable until the clip passes privacy validation.</p>}
        {mediaError && <p role="alert" className="text-sm text-red-700">{mediaError}</p>}
        <ul className="space-y-3">{evidence.map((asset) => <li key={asset.evidence_id} className="text-sm"><p className="break-words font-semibold">{asset.evidence_id} · {asset.start_s.toFixed(2)} video seconds · {asset.source}</p>{asset.media_url ? <a href={V2_BASE_URL + asset.media_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-vf-primary underline underline-offset-4">Open approved evidence</a> : <p className="mt-1 text-slate-600">Privacy review pending; media withheld.</p>}</li>)}</ul>
      </section>
      <section className="section-card space-y-5 p-5 sm:p-6"><h2 className="text-xl font-bold text-vf-navy">{editable ? "Edit draft" : "Report"}</h2>
        <label className="block font-semibold">Summary<textarea rows={4} value={draft.summary} disabled={!editable || working} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base disabled:bg-slate-50" /></label>
        <h3 className="text-lg font-semibold">Timeline</h3>
        {draft.timeline.map((item, index) => <div key={index} className="space-y-2 border-t border-slate-200 pt-4">
          <Button variant="ghost" onClick={() => seek(item.time_s)} disabled={!clip}>{item.time_s.toFixed(2)} video seconds</Button>
          <label className="block text-sm font-semibold">Observation {index + 1}<textarea rows={2} disabled={!editable || working} value={item.observation} onChange={(event) => setDraft({ ...draft, timeline: draft.timeline.map((entry, i) => i === index ? { ...entry, observation: event.target.value } : entry) })} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base disabled:bg-slate-50" /></label>
          <p className="break-words text-sm text-slate-600">{item.certainty} · {item.source} · {item.evidence_ids.join(", ") || "No supporting evidence"}</p>
        </div>)}
        <h3 className="text-lg font-semibold">Factors</h3>
        {draft.factors.map((item, index) => <label key={index} className="block text-sm font-semibold">{item.category} · {item.claim_status}<input value={item.label} disabled={!editable || working} onChange={(event) => setDraft({ ...draft, factors: draft.factors.map((entry, i) => i === index ? { ...entry, label: event.target.value } : entry) })} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base disabled:bg-slate-50" /><span className="mt-1 block break-words font-normal text-slate-600">Evidence: {item.evidence_ids.join(", ") || "Unknown"}</span></label>)}
        <h3 className="text-lg font-semibold">Unknowns</h3><ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">{draft.unknowns.map((item, index) => <li key={index}>{item}</li>)}</ul>
        {editable && <Button onClick={() => void save()} disabled={working || !dirty}>{working ? "Saving…" : "Save changes"}</Button>}
      </section>
      <div className="flex flex-wrap gap-3">
        {session?.roles.includes("Engineer") && draft.review_status === "DRAFT" && <Button disabled={working || !!dirty} onClick={() => setDecision("submit")}>Submit for review</Button>}
        {session?.roles.includes("Engineer") && draft.review_status === "REJECTED" && <Button disabled={working} onClick={() => setDecision("reopen")}>Reopen report</Button>}
        {session?.roles.includes("Reviewer") && draft.review_status === "IN_REVIEW" && session.subject !== report.submitted_by && <><Button disabled={working} onClick={() => setDecision("approve")}>Approve report</Button><Button variant="danger" disabled={working} onClick={() => setDecision("reject")}>Reject report</Button></>}
        {dirty && <p className="self-center text-sm text-slate-600">Save your edits before submitting.</p>}
      </div>
      <AuditSection loading={auditLoading} error={auditError} events={audit.map((item) => ({ event_id: `${id}:${item.version}`, incident_id: report.recording_id, actor: item.actor, action: `${item.action} · Version ${item.version}${item.reason ? ` · ${item.reason}` : ""}`, metadata: {}, created_at: item.created_at }))} />
    </>}
    {decision && <DecisionDialog action={decision} reason={reason} setReason={setReason} busy={working} error={error} close={() => setDecision(undefined)} confirm={() => void transition()} />}
  </div>;
}

function DecisionDialog({ action, reason, setReason, busy, error, close, confirm }: { action: Decision; reason: string; setReason: (value: string) => void; busy: boolean; error: string; close: () => void; confirm: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const trigger = document.activeElement as HTMLElement | null; const node = dialog.current; node?.showModal(); return () => { node?.close(); trigger?.focus(); }; }, []);
  return <dialog ref={dialog} aria-labelledby="v2-decision-title" onCancel={(event) => { event.preventDefault(); if (!busy) close(); }} className="w-[calc(100%-2rem)] max-w-md space-y-5 rounded-xl bg-white p-6 shadow-xl backdrop:bg-vf-navy/35">
    <h2 id="v2-decision-title" className="text-xl font-bold text-vf-navy">Confirm {action}</h2>
    <p className="text-sm text-slate-700">This records your decision in the report history.</p>
    {action === "reject" && <label className="block text-sm font-semibold">Rejection reason<textarea autoFocus required rows={3} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base" /></label>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap justify-end gap-3"><Button variant="ghost" onClick={close} disabled={busy}>Cancel</Button><Button onClick={confirm} disabled={busy || (action === "reject" && !reason.trim())}>Confirm {action}</Button></div>
  </dialog>;
}

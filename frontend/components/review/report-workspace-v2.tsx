"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { AuditSection } from "./audit-section";
import { ReviewTabs, type ReviewView } from "./review-tabs";
import { ReportExport } from "./report-export";
import { ArrowLeft } from "@/components/icons";
import { VideoPlayer, type VideoPlayerHandle, type VideoPlaybackState } from "./video-player";
import { TelemetryPanel } from "./telemetry-panel";
import { StatusBadge } from "@/components/ui/status-badge";
import { V2_BASE_URL, v2Error, v2Request } from "@/services/v2.service";
import { clearDraftRecovery, readDraftRecovery, writeDraftRecovery, type DraftRecovery } from "@/lib/draft-recovery";
import { useUnsavedChanges } from "@/lib/use-unsaved-changes";
import type { AnalysisV2, AuditV2, EvidenceV2, PageV2, ReportV2, SessionV2 } from "@/types/v2";

type DraftFields = { summary: string; timeline: string[]; factors: string[] };
function isDraftFields(value: unknown): value is DraftFields {
  if (!value || typeof value !== "object") return false;
  const fields = value as Record<string, unknown>;
  return typeof fields.summary === "string" && Array.isArray(fields.timeline) && fields.timeline.every((item) => typeof item === "string") && Array.isArray(fields.factors) && fields.factors.every((item) => typeof item === "string");
}
function fieldsOf(analysis: AnalysisV2): DraftFields {
  return { summary: analysis.summary, timeline: analysis.timeline.map((item) => item.observation), factors: analysis.factors.map((item) => item.label) };
}
function applyFields(analysis: AnalysisV2, fields: DraftFields): AnalysisV2 {
  return { ...structuredClone(analysis), summary: fields.summary, timeline: analysis.timeline.map((item, index) => ({ ...item, observation: fields.timeline[index] })), factors: analysis.factors.map((item, index) => ({ ...item, label: fields.factors[index] })) };
}

type Decision = "submit" | "approve" | "reject" | "reopen";

export function ReportWorkspaceV2({ id }: { id: string }) {
  const [view, setView] = useState<ReviewView>("overview");
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
  const video = useRef<VideoPlayerHandle>(null);
  const [playback, setPlayback] = useState<VideoPlaybackState>({ currentTime: 0, duration: 0, ready: false });
  const requestInFlight = useRef(false);
  const loadSequence = useRef(0);
  const [recoveryKey, setRecoveryKey] = useState("");
  const [recoveryNotice, setRecoveryNotice] = useState("");
  const [staleRecovery, setStaleRecovery] = useState<DraftRecovery<DraftFields>>();
  const loadAudit = useCallback(async () => {
    setAuditLoading(true); setAuditError("");
    try { setAudit((await v2Request<PageV2<AuditV2>>(`/reports/${id}/audit`)).items); }
    catch (cause) { setAuditError(v2Error(cause)); }
    finally { setAuditLoading(false); }
  }, [id]);
  const load = useCallback(async (discardRecovery = false) => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    const sequence = ++loadSequence.current;
    setWorking(true); setError("");
    try {
      const [data, assets, identity] = await Promise.all([v2Request<ReportV2>(`/reports/${id}`), v2Request<PageV2<EvidenceV2>>(`/reports/${id}/evidence`), v2Request<SessionV2>("/session")]);
      if (sequence !== loadSequence.current) return;
      const key = `v2:${encodeURIComponent(identity.subject)}:${id}`;
      const recovered = !discardRecovery && identity.roles.includes("Engineer") ? readDraftRecovery(key, isDraftFields) : null;
      let restored = structuredClone(data.analysis);
      setStaleRecovery(undefined); setRecoveryNotice("");
      if (discardRecovery && !clearDraftRecovery(key)) setRecoveryNotice("The recovery copy could not be removed from browser storage. It may reappear when you return.");
      else if (recovered) {
        if (data.analysis.review_status === "DRAFT" && recovered.version === data.version && recovered.value.timeline.length === data.analysis.timeline.length && recovered.value.factors.length === data.analysis.factors.length) {
          restored = applyFields(data.analysis, recovered.value);
          setRecoveryNotice("Unsaved edits restored from this tab.");
        } else setStaleRecovery(recovered);
      }
      setRecoveryKey(key); setReport(data); setDraft(restored); setEvidence(assets.items); setSession(identity);
      await loadAudit();
    } catch (cause) { if (sequence === loadSequence.current) setError(v2Error(cause)); }
    finally { if (sequence === loadSequence.current) { requestInFlight.current = false; setWorking(false); } }
  }, [id, loadAudit]);
  const invalidateRequests = useCallback(() => { loadSequence.current += 1; requestInFlight.current = false; }, []);
  useEffect(() => { void load(); return invalidateRequests; }, [load, invalidateRequests]);
  const editable = report?.analysis.review_status === "DRAFT" && session?.roles.includes("Engineer");
  const dirty = report && draft && JSON.stringify(report.analysis) !== JSON.stringify(draft);
  useUnsavedChanges(!!dirty || !!staleRecovery, working && !!report);
  function edit(next: AnalysisV2) {
    if (!editable || requestInFlight.current || !report || staleRecovery) return;
    setDraft(next); setRecoveryNotice("");
    if (JSON.stringify(report.analysis) === JSON.stringify(next)) clearDraftRecovery(recoveryKey);
    else if (!writeDraftRecovery(recoveryKey, report.version, fieldsOf(next))) setRecoveryNotice("Browser storage is unavailable. Keep this page open until your edits are saved.");
  }
  async function save() {
    if (!editable || !report || !draft || requestInFlight.current || staleRecovery) return;
    requestInFlight.current = true;
    const sequence = loadSequence.current;
    setWorking(true); setError("");
    try {
      const updated = await v2Request<ReportV2>(`/reports/${id}`, { method: "PATCH", body: JSON.stringify({ expected_version: report.version, summary: draft.summary, timeline: draft.timeline, factors: draft.factors, unknowns: draft.unknowns }) });
      if (sequence !== loadSequence.current) return;
      const cleared = clearDraftRecovery(recoveryKey);
      setRecoveryNotice(cleared ? "" : "The saved recovery copy could not be removed. It may reappear when you return."); setStaleRecovery(undefined); setReport(updated); setDraft(structuredClone(updated.analysis)); await loadAudit();
    } catch (cause) { if (sequence === loadSequence.current) setError(v2Error(cause)); }
    finally { if (sequence === loadSequence.current) { requestInFlight.current = false; setWorking(false); } }
  }
  async function transition() {
    if (!report || !decision || requestInFlight.current || (decision === "submit" && (dirty || staleRecovery))) return;
    requestInFlight.current = true;
    const sequence = loadSequence.current;
    setWorking(true); setError("");
    try {
      const updated = await v2Request<ReportV2>(`/reports/${id}/${decision}`, { method: "POST", body: JSON.stringify({ expected_version: report.version, ...(decision === "reject" ? { reason } : {}) }) });
      if (sequence !== loadSequence.current) return;
      const cleared = clearDraftRecovery(recoveryKey);
      setRecoveryNotice(cleared ? "" : "The saved recovery copy could not be removed. It may reappear when you return."); setStaleRecovery(undefined); setReport(updated); setDraft(structuredClone(updated.analysis)); setDecision(undefined); setReason(""); await loadAudit();
    } catch (cause) { if (sequence === loadSequence.current) setError(v2Error(cause)); }
    finally { if (sequence === loadSequence.current) { requestInFlight.current = false; setWorking(false); } }
  }
  const clip = evidence.find((asset) => asset.media_type === "video/mp4" && asset.media_url);
  function seek(time_s: number) {
    if (!clip || !video.current) return;
    const relative = time_s - clip.start_s;
    if (relative >= 0 && relative <= clip.end_s - clip.start_s) video.current.seekTo(relative, false);
  }
  return <div className="report-workspace">
    <header className="report-header"><div className="report-header-identity">{report && <Link href={`/recordings/${encodeURIComponent(report.recording_id)}`} aria-label="Back to recording" title="Back to recording" className="report-back"><ArrowLeft className="h-4 w-4" /></Link>}<div className="min-w-0"><p className="report-header-caption">Report review</p><h1 className="report-header-title">{id}</h1></div></div><div className="report-header-actions">{report && <><StatusBadge status={report.analysis.review_status} /><span className="report-version">v{report.version}</span><ReportExport id={id} report={report} dirty={!!dirty} /></>}<Button variant="ghost" onClick={() => { if ((!dirty && !staleRecovery) || window.confirm("Discard unsaved edits and load the latest report?")) void load(true); }} disabled={working}>Reload latest report</Button></div></header>
    {!report && !error && <p role="status">Loading report and evidence…</p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {report && draft && <>
      {recoveryNotice && <p role="status" className="text-sm text-slate-700">{recoveryNotice}</p>}
      {staleRecovery && <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><p>A saved draft from version {staleRecovery.version} is available. The server report changed or is read-only. Copy any saved text you need before discarding this recovery copy.</p><details className="mt-2"><summary className="cursor-pointer font-semibold">View saved edits</summary><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words">{JSON.stringify(staleRecovery.value, null, 2)}</pre></details><Button variant="ghost" disabled={working} onClick={() => { if (window.confirm("Discard the older saved draft?")) { if (clearDraftRecovery(recoveryKey)) setStaleRecovery(undefined); else setRecoveryNotice("The saved draft could not be removed. Browser storage is unavailable."); } }}>Discard saved draft</Button></section>}
      <div className="report-workflow flex flex-wrap items-center gap-2" hidden={view !== "report"}>
        {session?.roles.includes("Engineer") && draft.review_status === "DRAFT" && <Button disabled={working || !!dirty || !!staleRecovery} onClick={() => setDecision("submit")}>Submit for review</Button>}
        {session?.roles.includes("Engineer") && draft.review_status === "REJECTED" && <Button disabled={working} onClick={() => setDecision("reopen")}>Reopen report</Button>}
        {session?.roles.includes("Reviewer") && draft.review_status === "IN_REVIEW" && session.subject !== report.submitted_by && <><Button disabled={working} onClick={() => setDecision("approve")}>Approve report</Button><Button variant="danger" disabled={working} onClick={() => setDecision("reject")}>Reject report</Button></>}
        {dirty && <p className="self-center text-sm text-slate-600">Save your edits before submitting.</p>}
        {draft.review_status === "IN_REVIEW" && <p className="text-sm text-slate-600">{session?.subject === report.submitted_by ? "Another authorized reviewer must review your submission." : session?.roles.includes("Reviewer") ? "Review the evidence before recording your decision." : "Awaiting a decision from an authorized reviewer."}</p>}
        {draft.review_status === "APPROVED" && <p className="text-sm text-emerald-700">Report approved. This report is read-only.</p>}
        {draft.review_status === "DRAFT" && !session?.roles.includes("Engineer") && <p className="text-sm text-slate-600">An authorized engineer can prepare and submit this draft.</p>}
      </div>
    <ReviewTabs value={view} onChange={(next) => { if (next === "history") video.current?.pause(); setView(next); }} disabled={working} />
      <div className="review-content" hidden={view === "history"}>
      <div data-view={view} className="review-layout review-focused-layout review-pinned-layout">
      <div className="review-pinned-video min-w-0">
        {clip?.media_url ? <VideoPlayer ref={video} onPlaybackChange={setPlayback} ariaLabel="Approved masked incident clip" src={V2_BASE_URL + clip.media_url} start={null} critical={null} end={null} /> : <p className="text-sm text-slate-600">Video playback is unavailable until the clip passes privacy validation.</p>}
        <section className="section-card p-5"><h2 className="text-lg font-semibold text-vf-navy">Analysis summary</h2><p className="mt-3 text-sm leading-7 text-slate-600">{report.analysis.summary}</p></section>
      </div>
      <div className="review-analysis-column min-w-0">
      <div className="review-evidence min-w-0" hidden={view === "report"}>
      <div className="review-media-pane min-w-0">
        <TelemetryPanel key={report.recording_id} id={report.recording_id} kind="recording" currentTime={playback.currentTime + (clip?.start_s ?? 0)} seekEnabled={!!clip && playback.ready} window={draft.window} seekRange={clip ? { start_s: clip.start_s, end_s: Math.min(clip.end_s, clip.start_s + playback.duration) } : undefined} onSeek={(time) => { if (clip && time >= clip.start_s && time <= clip.end_s) video.current?.seekTo(time - clip.start_s, false); }} />
      </div>
      <div className="review-assets-pane min-w-0">
      <section className="section-card space-y-4 p-5 sm:p-6"><h2 className="text-xl font-bold text-vf-navy">Evidence</h2>
        <ul className="space-y-3">{evidence.map((asset) => <li key={asset.evidence_id} className="text-sm"><p className="break-words font-semibold">{asset.evidence_id} · {asset.start_s.toFixed(2)} video seconds · {asset.source}</p>{asset.media_url ? <a href={V2_BASE_URL + asset.media_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-vf-primary underline underline-offset-4">Open approved evidence</a> : <p className="mt-1 text-slate-600">Privacy review pending; media withheld.</p>}</li>)}</ul>
      </section>
      </div></div>
      <div className="review-details min-w-0" hidden={view !== "report"}><section className="review-report section-card min-w-0 p-5 sm:p-6"><h2 className="text-xl font-bold text-vf-navy">{editable ? "Edit draft" : "Report"}</h2>
        <label className="block font-semibold">Summary<textarea rows={4} value={draft.summary} disabled={!editable || working || !!staleRecovery} onChange={(event) => edit({ ...draft, summary: event.target.value })} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base disabled:bg-slate-50" /></label>
        <h3 className="text-lg font-semibold">Timeline</h3>
        {draft.timeline.map((item, index) => <div key={index} className="space-y-2 border-t border-slate-200 pt-4">
          <Button variant="ghost" onClick={() => seek(item.time_s)} disabled={!clip}>{item.time_s.toFixed(2)} video seconds</Button>
          <label className="block text-sm font-semibold">Observation {index + 1}<textarea rows={2} disabled={!editable || working || !!staleRecovery} value={item.observation} onChange={(event) => edit({ ...draft, timeline: draft.timeline.map((entry, i) => i === index ? { ...entry, observation: event.target.value } : entry) })} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base disabled:bg-slate-50" /></label>
          <p className="break-words text-sm text-slate-600">{item.certainty} · {item.source} · {item.evidence_ids.join(", ") || "No supporting evidence"}</p>
        </div>)}
        <h3 className="text-lg font-semibold">Factors</h3>
        {draft.factors.map((item, index) => <label key={index} className="block text-sm font-semibold">{item.category} · {item.claim_status}<input value={item.label} disabled={!editable || working || !!staleRecovery} onChange={(event) => edit({ ...draft, factors: draft.factors.map((entry, i) => i === index ? { ...entry, label: event.target.value } : entry) })} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base disabled:bg-slate-50" /><span className="mt-1 block break-words font-normal text-slate-600">Evidence: {item.evidence_ids.join(", ") || "Unknown"}</span></label>)}
        <h3 className="text-lg font-semibold">Unknowns</h3><ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">{draft.unknowns.map((item, index) => <li key={index}>{item}</li>)}</ul>
        {editable && <Button onClick={() => void save()} disabled={working || !dirty || !!staleRecovery}>{working ? "Saving…" : "Save changes"}</Button>}
      </section>

      </div></div></div></div>
      <div className="review-history" hidden={view !== "history"}><AuditSection loading={auditLoading} error={auditError} events={audit.map((item) => ({ event_id: `${id}:${item.version}`, incident_id: report.recording_id, actor: item.actor, action: `${item.action} · Version ${item.version}${item.reason ? ` · ${item.reason}` : ""}`, metadata: {}, created_at: item.created_at }))} /></div>
    </>}
    {decision && <DecisionDialog action={decision} reason={reason} setReason={setReason} busy={working} error={error} close={() => { if (!requestInFlight.current) setDecision(undefined); }} confirm={() => void transition()} />}
  </div>;
}

function DecisionDialog({ action, reason, setReason, busy, error, close, confirm }: { action: Decision; reason: string; setReason: (value: string) => void; busy: boolean; error: string; close: () => void; confirm: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const trigger = document.activeElement as HTMLElement | null; const node = dialog.current; node?.showModal(); return () => { node?.close(); trigger?.focus(); }; }, []);
  return <dialog ref={dialog} aria-labelledby="v2-decision-title" onCancel={(event) => { event.preventDefault(); if (!busy) close(); }} className="w-[calc(100%-2rem)] max-w-md space-y-5 rounded-xl bg-white p-6 shadow-xl backdrop:bg-vf-navy/35">
    <h2 id="v2-decision-title" className="text-xl font-bold text-vf-navy">Confirm {action}</h2>
    <p className="text-sm text-slate-700">This records your decision in the report history.</p>
    {action === "reject" && <label className="block text-sm font-semibold">Rejection reason<textarea autoFocus required rows={3} disabled={busy} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base" /></label>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap justify-end gap-3"><Button variant="ghost" onClick={close} disabled={busy}>Cancel</Button><Button onClick={confirm} disabled={busy || (action === "reject" && !reason.trim())}>Confirm {action}</Button></div>
  </dialog>;
}

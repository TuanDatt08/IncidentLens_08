"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft } from "@/components/icons";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { toVideoTime } from "@/lib/video-time";
import { getEvidence } from "@/services/evidence.service";
import { getIncident, getIncidentPreviewStatus, getIncidentVideoUrl } from "@/services/incident.service";
import { getIncidentReport } from "@/services/report.service";
import { getIncidentAudit } from "@/services/audit.service";
import type { IncidentDraft } from "@/types/incident";
import { EvidenceSection } from "./evidence-section";
import { IncidentSummary } from "./incident-summary";
import { IncidentTimeline } from "./incident-timeline";
import { ReportEditor, type EditorState } from "./report-editor";
import { VideoPlayer, type VideoPlayerHandle, type VideoPlaybackState } from "./video-player";
import { AnalysisContext, AnalysisContextProvider } from "./analysis-context";
import { WorkflowActions } from "./workflow-actions";
import { AuditSection } from "./audit-section";
import { ReviewTabs, type ReviewView } from "./review-tabs";
import { ReportExport } from "./report-export";

// Reset child editors/media before an old incident can flash onscreen.
export function ReviewWorkspace({ id }: { id: string }) {
  return <AnalysisContextProvider key={id} id={id}><IncidentReview id={id} /></AnalysisContextProvider>;
}

// Page-local resource state; each API has its own response lifetime and retry.
function useReviewResource<T>(id: string, load: (id: string) => Promise<T>) {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    void load(id).then((value) => { if (active) setData(value); })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "The request could not be completed."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, load, attempt]);
  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return { data, setData, loading, error, retry };
}

function IncidentReview({ id }: { id: string }) {
  const [view, setView] = useState<ReviewView>("overview");
  const metadata = useReviewResource(id, getIncident);
  const preview = useReviewResource(id, getIncidentPreviewStatus);
  const report = useReviewResource(id, getIncidentReport);
  const evidence = useReviewResource(id, getEvidence);
  const audit = useReviewResource(id, getIncidentAudit);
  const [editorState, setEditorState] = useState<EditorState>({ dirty: true, saving: false });
  const videoPlayer = useRef<VideoPlayerHandle>(null);
  const inspectionColumn = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const column = inspectionColumn.current;
    if (!column) return;
    const wheel = (event: WheelEvent) => {
      if (event.ctrlKey || event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
      // Keep scrollable JSON, text editors and select controls native.
      if ((event.target as Element)?.closest("pre, textarea, select, dialog")) return;
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? column.clientHeight : 1);
      const maximum = column.scrollHeight - column.clientHeight;
      if (maximum <= 1) return;
      const next = Math.max(0, Math.min(maximum, column.scrollTop + delta));
      if (Math.abs(next - column.scrollTop) < .5) return;
      event.preventDefault();
      column.scrollTop = next;
    };
    column.addEventListener("wheel", wheel, { passive: false });
    return () => column.removeEventListener("wheel", wheel);
  }, []);
  const [playback, setPlayback] = useState<VideoPlaybackState>({ currentTime: 0, duration: 0, ready: false });
  const incident = metadata.data;
  const draft = report.data;
  const videoTime = (relative: number) => toVideoTime(relative, incident?.video_metadata?.collision_offset_in_video_s, incident?.video_metadata?.duration);
  const previewReady = preview.data?.state === "ready";
  const retryPreview = preview.retry;
  useEffect(() => {
    if (preview.data?.state !== "pending" || preview.loading || preview.error) return;
    const timer = setTimeout(retryPreview, 5000);
    return () => clearTimeout(timer);
  }, [preview.data?.state, preview.loading, preview.error, retryPreview]);
  const seekEnabled = !!incident && previewReady && videoTime(0) !== null;
  const seekRelative = (relative: number) => {
    const target = videoTime(relative);
    if (target !== null) videoPlayer.current?.seekTo(target);
  };
  function reportUpdated(updated: IncidentDraft) {
    report.setData(updated);
    // Initial report hydration does not trigger a second audit request.
    if (updated.version !== draft?.version) audit.retry();
  }
  const incidentWindow = draft?.incident_window;
  return <div className="report-workspace" data-review-view={view}>
    <header className="report-header">
      <div className="report-header-identity"><Link href="/incidents" aria-label="Back to incidents" title="Back to incidents" className="report-back"><ArrowLeft className="h-4 w-4" /></Link><div className="min-w-0"><p className="report-header-caption">Incident review</p><h1 className="report-header-title">{id}</h1></div></div>
      <div className="report-header-actions">{draft && <><StatusBadge status={draft.review_status} /><span className="report-version">v{draft.version}</span><ReportExport id={id} report={draft} dirty={editorState.dirty} evidence={evidence.data ?? []} /></>}</div>
    </header>
    <ReviewTabs value={view} onChange={(next) => { if (next === "history") videoPlayer.current?.pause(); setView(next); }} disabled={editorState.saving} />
    {draft && view === "report" && <WorkflowActions id={id} draft={draft} onUpdated={reportUpdated} editorState={editorState} />}
    {[metadata, preview, report, evidence].some((resource) => resource.loading || resource.error) && <div className="review-resource-states">
      <ResourceState name="metadata" loading={metadata.loading} error={metadata.error} retry={metadata.retry} />
      <ResourceState name="video preview" loading={preview.loading} error={preview.error} retry={preview.retry} />
      <ResourceState name="report" loading={report.loading} error={report.error} retry={report.retry} />
      <ResourceState name="evidence" loading={evidence.loading} error={evidence.error} retry={evidence.retry} />
    </div>}
    {preview.data?.state === "pending" && <section className="section-card space-y-3 p-5 sm:p-6" aria-label="Video preview status">
      <p role="status" className="text-sm text-slate-600">Video preview is being prepared. Analysis jobs take priority; this may take a while.</p>
      <Button variant="ghost" disabled={preview.loading} onClick={preview.retry}>Retry video preview</Button>
    </section>}
    <div className="review-content">
      <div data-view={view} className="review-layout review-focused-layout review-pinned-layout">
        <div className="review-pinned-video min-w-0">
          {incident && previewReady && <VideoPlayer ref={videoPlayer} onPlaybackChange={setPlayback} src={getIncidentVideoUrl(incident.incident_id)} start={incidentWindow ? videoTime(incidentWindow.start) : null} critical={incidentWindow ? videoTime(incidentWindow.critical) : null} end={incidentWindow ? videoTime(incidentWindow.end) : null} />}
          {draft?.incident_window && <IncidentTimeline draft={draft} onSeek={seekRelative} seekEnabled={seekEnabled} />}
        </div>
        <div ref={inspectionColumn} className="review-analysis-column min-w-0" role="region" aria-label="Nội dung kiểm tra sự cố" tabIndex={0}>
          <AnalysisContext mode="telemetry" id={id} currentTime={playback.currentTime} seekEnabled={previewReady && playback.ready} onSeek={(time) => videoPlayer.current?.seekTo(time, false)} />
        <div className="review-evidence min-w-0" hidden={view !== "overview"}>
          <div className="review-media-pane min-w-0">
          {draft && <IncidentSummary draft={draft} />}
          <AnalysisContext mode="analysis" id={id} currentTime={playback.currentTime} seekEnabled={previewReady && playback.ready} onSeek={(time) => videoPlayer.current?.seekTo(time, false)} />
          </div>
          <div className="review-assets-pane min-w-0">
          {evidence.data !== undefined && <EvidenceSection incidentId={id} evidence={evidence.data} onSeek={seekRelative} seekEnabled={seekEnabled} />}
          </div>
        </div>
        <div className="review-details min-w-0" hidden={view !== "report"}>
          <div className="review-report min-w-0">
            {draft && <ReportEditor id={id} draft={draft} onSaved={reportUpdated} onStateChange={setEditorState} />}
          </div>
        </div>
    <div className="review-history" hidden={view !== "history"}>
      <AuditSection events={audit.data ?? []} loading={audit.loading} error={audit.error} />
      {audit.error && <Button variant="ghost" disabled={audit.loading} onClick={audit.retry}>Retry audit</Button>}
    </div>
        </div>
      </div>
    </div>
  </div>;
}

function ResourceState({ name, loading, error, retry }: { name: string; loading: boolean; error: string; retry: () => void }) {
  if (!loading && !error) return null;
  return <section className="review-resource-state" aria-label={name + " loading status"} aria-busy={loading}>
    {loading && <p role="status" className="text-sm text-slate-600">Loading {name}…</p>}
    {error && <><p role="alert" className="text-sm font-semibold text-red-700">Could not load {name}: {error}</p><Button variant="ghost" disabled={loading} onClick={retry}>Retry {name}</Button></>}
  </section>;
}

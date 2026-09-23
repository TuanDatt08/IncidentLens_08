"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, CircleAlert, FileVideo } from "@/components/icons";
import { StatusBadge } from "@/components/ui/status-badge";
import { toVideoTime } from "@/lib/video-time";
import { getEvidence } from "@/services/evidence.service";
import { getIncident, getIncidentVideoUrl } from "@/services/incident.service";
import { getIncidentReport } from "@/services/report.service";
import type { Evidence } from "@/types/evidence";
import type { IncidentDraft, IncidentRecord } from "@/types/incident";
import { EvidenceSection } from "./evidence-section";
import { IncidentSummary } from "./incident-summary";
import { IncidentTimeline } from "./incident-timeline";
import { ReportEditor } from "./report-editor";
import { VideoPlayer, type VideoPlayerHandle } from "./video-player";
import { WorkflowActions } from "./workflow-actions";

export function ReviewWorkspace({ id }: { id: string }) {
  const [incident, setIncident] = useState<IncidentRecord>();
  const [draft, setDraft] = useState<IncidentDraft>();
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [error, setError] = useState("");
  const videoPlayer = useRef<VideoPlayerHandle>(null);

  useEffect(() => {
    let active = true;
    setIncident(undefined);
    setDraft(undefined);
    setEvidence([]);
    setError("");
    Promise.all([getIncident(id), getIncidentReport(id), getEvidence(id)])
      .then(([incidentData, draftData, evidenceData]) => {
        if (!active) return;
        setIncident(incidentData);
        setDraft(draftData);
        setEvidence(evidenceData);
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (error) return <div className="mx-auto max-w-[760px] py-16 text-center"><span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-red-50 text-red-600"><CircleAlert className="h-6 w-6" /></span><h1 className="mt-5 text-2xl font-extrabold text-vf-navy">Unable to load incident</h1><p className="mt-2 text-sm font-semibold text-slate-500">{error}</p><Link href="/incidents" className="mt-6 inline-flex items-center gap-2 text-sm font-extrabold text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link></div>;
  if (!incident || !draft) return <ReviewSkeleton />;

  const offset = incident.video_metadata?.collision_offset_in_video_s;
  const duration = incident.video_metadata?.duration;
  const incidentWindow = draft.incident_window;
  const videoTime = (relativeTime: number) => toVideoTime(relativeTime, offset, duration);
  const seekEnabled = videoTime(0) !== null;
  const seekRelative = (relativeTime: number) => {
    const target = videoTime(relativeTime);
    if (target !== null) videoPlayer.current?.seekTo(target);
  };

  return <div className="space-y-6"><div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><Link href="/incidents" className="mb-5 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link><div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-vf-navy text-white"><FileVideo className="h-5 w-5" /></span><div><p className="eyebrow">Incident review</p><h1 className="mt-1 text-2xl font-extrabold tracking-[-0.04em] text-vf-navy sm:text-3xl">{incident.incident_id}</h1><p className="mt-1 max-w-[420px] truncate text-xs font-semibold text-slate-400">{incident.incident_record?.scenario?.replaceAll("_", " ") ?? (incident.video_metadata ? `${incident.video_metadata.duration.toFixed(1)}s video` : "Video metadata unavailable")}</p></div></div></div><div className="flex items-center gap-3"><span className="text-xs font-bold text-slate-400">Report status</span><StatusBadge status={draft.review_status} /></div></div><div className="grid gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(360px,0.88fr)]"><VideoPlayer ref={videoPlayer} src={getIncidentVideoUrl(incident.incident_id)} start={incidentWindow ? videoTime(incidentWindow.start) : null} critical={incidentWindow ? videoTime(incidentWindow.critical) : null} end={incidentWindow ? videoTime(incidentWindow.end) : null} /><IncidentSummary draft={draft} /></div><IncidentTimeline draft={draft} onSeek={seekRelative} seekEnabled={seekEnabled} /><EvidenceSection incidentId={incident.incident_id} evidence={evidence} onSeek={seekRelative} seekEnabled={seekEnabled} /><ReportEditor id={id} draft={draft} onSaved={setDraft} /><WorkflowActions id={id} draft={draft} onUpdated={setDraft} /></div>;
}

function ReviewSkeleton() { return <div className="space-y-6"><div className="h-20 animate-pulse rounded-2xl bg-slate-100" /><div className="grid gap-6 lg:grid-cols-2"><div className="aspect-video animate-pulse rounded-2xl bg-slate-100" /><div className="h-80 animate-pulse rounded-2xl bg-slate-100" /></div><div className="h-52 animate-pulse rounded-2xl bg-slate-100" /></div>; }

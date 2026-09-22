"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, CircleAlert, FileVideo } from "@/components/icons";
import { StatusBadge } from "@/components/ui/status-badge";
import { getEvidence } from "@/services/evidence.service";
import { getIncident } from "@/services/incident.service";
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

  return <div className="space-y-6"><div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><Link href="/incidents" className="mb-5 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link><div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-vf-navy text-white"><FileVideo className="h-5 w-5" /></span><div><p className="eyebrow">Incident review</p><h1 className="mt-1 text-2xl font-extrabold tracking-[-0.04em] text-vf-navy sm:text-3xl">{incident.id}</h1><p className="mt-1 max-w-[420px] truncate text-xs font-semibold text-slate-400">{incident.file_name}</p></div></div></div><div className="flex items-center gap-3"><span className="text-xs font-bold text-slate-400">Report status</span><StatusBadge status={draft.status} /></div></div><div className="grid gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(360px,0.88fr)]"><VideoPlayer ref={videoPlayer} src={incident.video_url} start={draft.start_sec} critical={draft.critical_sec} end={draft.end_sec} /><IncidentSummary draft={draft} /></div><IncidentTimeline draft={draft} onSeek={(seconds) => videoPlayer.current?.seekTo(seconds)} /><EvidenceSection evidence={evidence} onSeek={(seconds) => videoPlayer.current?.seekTo(seconds)} /><ReportEditor draft={draft} onSaved={setDraft} /><WorkflowActions draft={draft} onUpdated={setDraft} /></div>;
}

function ReviewSkeleton() { return <div className="space-y-6"><div className="h-20 animate-pulse rounded-2xl bg-slate-100" /><div className="grid gap-6 lg:grid-cols-2"><div className="aspect-video animate-pulse rounded-2xl bg-slate-100" /><div className="h-80 animate-pulse rounded-2xl bg-slate-100" /></div><div className="h-52 animate-pulse rounded-2xl bg-slate-100" /></div>; }
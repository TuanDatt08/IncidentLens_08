"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Check, CircleAlert, Film, Gauge } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { analyzeIncident, subscribeToProgress } from "@/services/analysis.service";
import { getIncident } from "@/services/incident.service";
import type { IncidentRecord } from "@/types/incident";
import type { ProgressEvent } from "@/types/processing";

const stages = [
  { key: "UPLOADED", label: "Upload", detail: "Package received" },
  { key: "VALIDATING", label: "Validate", detail: "Checking media package" },
  { key: "EXTRACTING", label: "Extract", detail: "Preparing frames and signals" },
  { key: "SYNCHRONIZING", label: "Synchronize", detail: "Aligning video and log" },
  { key: "PASS_1", label: "Pass 1", detail: "Incident localization" },
  { key: "PASS_2", label: "Pass 2", detail: "Detailed analysis" },
  { key: "COMPLETED", label: "Complete", detail: "Draft report ready" },
] as const;

export function ProcessingView({ id }: { id: string }) {
  const [incident, setIncident] = useState<IncidentRecord>();
  const [progress, setProgress] = useState(0);
  const [event, setEvent] = useState<ProgressEvent>({ progress: 0, stage: "UPLOADED", message: "Preparing analysis package." });
  const [error, setError] = useState("");

  useEffect(() => {
    let unsubscribe: () => void = () => undefined;
    let active = true;

    async function start() {
      try {
        const data = await getIncident(id);
        if (!active) return;
        setIncident(data);
        if (data.processing_status === "COMPLETED") {
          setProgress(100);
          setEvent({ progress: 100, stage: "COMPLETED", message: "Analysis complete. Draft report is ready to review." });
          return;
        }
        await analyzeIncident(id);
        if (!active) return;
        unsubscribe = subscribeToProgress(id, (nextEvent) => {
          setProgress(nextEvent.progress);
          setEvent(nextEvent);
        }, (streamError) => setError(streamError.message));
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Analysis could not be started.");
      }
    }
    void start();
    return () => {
      active = false;
      unsubscribe();
    };
  }, [id]);

  const activeStageIndex = useMemo(() => {
    const index = stages.findIndex((stage) => stage.key === event.stage);
    return index < 0 ? 0 : index;
  }, [event.stage]);

  return <div className="mx-auto max-w-[980px]">
    <Link href="/incidents" className="mb-8 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link>
    <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><p className="eyebrow">{incident?.id ?? "Incident package"}</p><h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em] text-vf-navy sm:text-4xl">Analyzing Incident</h1><p className="mt-2 text-sm leading-6 text-slate-500">IncidentLens is processing your media package through the AI analysis pipeline.</p></div>{incident && <StatusBadge status={progress === 100 ? "COMPLETED" : "PROCESSING"} />}</div>

    {error && <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}

    <section className="section-card overflow-hidden">
      <div className="bg-vf-navy px-5 py-7 text-white sm:px-8"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-extrabold uppercase tracking-[0.14em] text-blue-200">AI pipeline</p><h2 className="mt-2 text-xl font-extrabold">{event.message ?? "Preparing analysis…"}</h2></div><span className="text-4xl font-extrabold tracking-[-0.06em] text-white">{progress}%</span></div><div className="mt-6 h-2 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-vf-primary transition-all duration-700" style={{ width: `${progress}%` }} /></div></div>
      <div className="p-5 sm:p-8"><div className="space-y-0">{stages.map((stage, index) => { const complete = index < activeStageIndex || progress === 100; const active = index === activeStageIndex && progress < 100; return <div key={stage.key} className="flex gap-4"><div className="flex flex-col items-center"><span className={`z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-4 border-white text-xs font-extrabold ${complete ? "bg-vf-primary text-white" : active ? "bg-blue-50 text-vf-primary ring-4 ring-blue-50" : "bg-slate-100 text-slate-400"}`}>{complete ? <Check className="h-4 w-4" /> : index + 1}</span>{index < stages.length - 1 && <span className={`w-0.5 flex-1 ${complete ? "bg-blue-200" : "bg-slate-100"}`} />}</div><div className={`min-h-[68px] pb-5 ${active ? "text-vf-navy" : "text-slate-500"}`}><div className="flex flex-wrap items-center gap-2"><p className={`text-sm font-extrabold ${active || complete ? "text-vf-navy" : "text-slate-400"}`}>{stage.label}</p>{active && <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-[0.08em] text-vf-primary">In progress</span>}</div><p className="mt-1 text-xs font-semibold">{stage.detail}</p></div></div>; })}</div></div>
    </section>

    <div className="mt-5 grid gap-4 sm:grid-cols-2"><InfoCard icon={<Film className="h-5 w-5" />} label="Source package" value={incident?.file_name ?? "Loading media package…"} /><InfoCard icon={<Gauge className="h-5 w-5" />} label="Analysis passes" value={progress >= 50 ? "Pass 1 complete · Pass 2 active" : "Pass 1 will begin at 50%"} /></div>
    {progress === 100 && <div className="mt-6 flex flex-col items-center justify-between gap-4 rounded-2xl border border-emerald-100 bg-emerald-50 p-5 sm:flex-row sm:px-6"><div><p className="font-extrabold text-emerald-900">Draft report ready</p><p className="mt-1 text-xs font-semibold text-emerald-700">Review the incident window, evidence and AI-generated report.</p></div><Link href={`/incidents/${id}`}><Button className="bg-emerald-600 hover:bg-emerald-700">Open review <ArrowRight className="h-4 w-4" /></Button></Link></div>}
  </div>;
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="section-card flex min-w-0 items-center gap-3 px-4 py-4"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-vf-primary">{icon}</span><span className="min-w-0"><span className="block text-[10px] font-extrabold uppercase tracking-[0.1em] text-slate-400">{label}</span><span className="mt-1 block truncate text-xs font-extrabold text-vf-navy">{value}</span></span></div>;
}
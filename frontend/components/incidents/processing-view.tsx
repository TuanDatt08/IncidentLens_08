"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Check, CircleAlert, Film, Gauge } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { analyzeIncident, clearStoredJobId, getAnalysisJob, getStoredJobId } from "@/services/analysis.service";
import { getEvidence } from "@/services/evidence.service";
import { getIncident } from "@/services/incident.service";
import { getIncidentReport } from "@/services/report.service";
import type { IncidentRecord } from "@/types/incident";
import type { AnalysisJob, JobStatus, ProcessingStage } from "@/types/processing";

const POLL_INTERVAL_MS = 2000;
const stages = [
  { key: "QUEUED", label: "Queued", detail: "Waiting for an analysis worker" },
  { key: "RUNNING", label: "Start", detail: "Starting the analysis job" },
  { key: "PASS_1", label: "Pass 1", detail: "Incident localization" },
  { key: "PASS_2", label: "Pass 2", detail: "Detailed analysis" },
  { key: "COMPLETED", label: "Complete", detail: "Draft report and evidence ready" },
] as const;

function jobStage(job: AnalysisJob): ProcessingStage {
  if (job.status === "succeeded") return "COMPLETED";
  if (job.status === "failed") return "FAILED";
  if (job.status === "cancelled") return "CANCELLED";
  if (job.status === "queued") return "QUEUED";
  if (job.pass === 2) return "PASS_2";
  if (job.pass === 1) return "PASS_1";
  return "RUNNING";
}

function jobProgress(job: AnalysisJob): number {
  if (job.status === "succeeded") return 100;
  if (job.status === "queued") return 0;
  const { done, total } = job.progress;
  const fraction = total && total > 0 ? Math.min(1, Math.max(0, done / total)) : 0;
  if (job.pass === 2) return Math.min(99, 50 + Math.round(fraction * 50));
  if (job.pass === 1) return Math.round(fraction * 50);
  return 0;
}

function jobMessage(job: AnalysisJob): string {
  if (job.status === "queued") return "Analysis queued. Waiting for a worker.";
  if (job.status === "failed") return job.error?.message ?? "Analysis failed.";
  if (job.status === "cancelled") return "Analysis was cancelled.";
  if (job.status === "succeeded") return "Analysis complete. Loading report and evidence.";
  if (job.pass === 1) return `Pass 1: incident localization (${job.progress.done}/${job.progress.total ?? "?"}).`;
  if (job.pass === 2) return `Pass 2: detailed analysis (${job.progress.done}/${job.progress.total ?? "?"}).`;
  return "Analysis is starting.";
}

export function ProcessingView({ id }: { id: string }) {
  const [incident, setIncident] = useState<IncidentRecord>();
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState<JobStatus>("queued");
  const [lastPass, setLastPass] = useState<1 | 2 | null>(null);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<ProcessingStage>("QUEUED");
  const [message, setMessage] = useState("Preparing analysis package.");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function loadOutputs() {
      await Promise.all([getIncidentReport(id), getEvidence(id)]);
      if (!active) return;
      setReady(true);
      setMessage("Analysis complete. Draft report and evidence are ready to review.");
    }

    async function poll(currentJobId: string) {
      let terminal = false;
      try {
        const job = await getAnalysisJob(currentJobId);
        if (!active) return;
        setError("");
        setJobStatus(job.status);
        setLastPass(job.pass);
        setStage(jobStage(job));
        setProgress(jobProgress(job));
        setMessage(jobMessage(job));

        if (job.status === "succeeded") {
          terminal = true;
          clearStoredJobId(id);
          await loadOutputs();
          return;
        }
        if (job.status === "failed" || job.status === "cancelled") {
          terminal = true;
          clearStoredJobId(id);
          setError(jobMessage(job));
          return;
        }
        timer = setTimeout(() => void poll(currentJobId), POLL_INTERVAL_MS);
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Analysis status could not be loaded.");
          if (!terminal) timer = setTimeout(() => void poll(currentJobId), POLL_INTERVAL_MS);
        }
      }
    }

    async function start() {
      try {
        const data = await getIncident(id);
        if (!active) return;
        setIncident(data);
        if (data.processing_status === "COMPLETED") {
          clearStoredJobId(id);
          setJobStatus("succeeded");
          setStage("COMPLETED");
          setProgress(100);
          await loadOutputs();
          return;
        }
        const storedJobId = getStoredJobId(id);
        const currentJobId = storedJobId ?? (await analyzeIncident(id)).job_id;
        if (!active) return;
        setJobId(currentJobId);
        await poll(currentJobId);
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Analysis could not be started.");
      }
    }

    void start();
    return () => {
      active = false;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [id]);

  const activeStageIndex = useMemo(() => {
    if (stage === "FAILED" || stage === "CANCELLED") return lastPass === 2 ? 3 : lastPass === 1 ? 2 : 1;
    return stages.findIndex((item) => item.key === stage);
  }, [stage, lastPass]);
  const statusLabel = jobStatus === "succeeded" ? "Completed" : jobStatus === "running" ? "Running" : jobStatus === "failed" ? "Failed" : jobStatus === "cancelled" ? "Cancelled" : "Queued";
  const statusStyle = jobStatus === "succeeded" ? "bg-emerald-50 text-emerald-700" : jobStatus === "failed" || jobStatus === "cancelled" ? "bg-red-50 text-red-700" : "bg-blue-50 text-blue-700";
  const passLabel = stage === "PASS_2" ? "Pass 2 active" : stage === "PASS_1" ? "Pass 1 active" : jobStatus === "succeeded" ? "Both passes complete" : "Waiting for pass 1";

  return <div className="mx-auto max-w-[980px]">
    <Link href="/incidents" className="mb-8 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link>
    <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><p className="eyebrow">{incident?.incident_id ?? "Incident package"}</p><h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em] text-vf-navy sm:text-4xl">Analyzing Incident</h1><p className="mt-2 text-sm leading-6 text-slate-500">IncidentLens is processing your media package through the AI analysis pipeline.</p></div>{incident && <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-extrabold uppercase tracking-[0.04em] ${statusStyle}`}>{statusLabel}</span>}</div>

    {error && <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}

    <section className="section-card overflow-hidden">
      <div className="bg-vf-navy px-5 py-7 text-white sm:px-8"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-extrabold uppercase tracking-[0.14em] text-blue-200">AI pipeline{jobId ? ` · ${jobId}` : ""}</p><h2 className="mt-2 text-xl font-extrabold">{message}</h2></div><span className="text-4xl font-extrabold tracking-[-0.06em] text-white">{progress}%</span></div><div className="mt-6 h-2 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-vf-primary transition-all duration-700" style={{ width: `${progress}%` }} /></div></div>
      <div className="p-5 sm:p-8"><div className="space-y-0">{stages.map((item, index) => { const complete = index < activeStageIndex || ready; const current = index === activeStageIndex && !ready; return <div key={item.key} className="flex gap-4"><div className="flex flex-col items-center"><span className={`z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-4 border-white text-xs font-extrabold ${complete ? "bg-vf-primary text-white" : current ? "bg-blue-50 text-vf-primary ring-4 ring-blue-50" : "bg-slate-100 text-slate-400"}`}>{complete ? <Check className="h-4 w-4" /> : index + 1}</span>{index < stages.length - 1 && <span className={`w-0.5 flex-1 ${complete ? "bg-blue-200" : "bg-slate-100"}`} />}</div><div className={`min-h-[68px] pb-5 ${current ? "text-vf-navy" : "text-slate-500"}`}><div className="flex flex-wrap items-center gap-2"><p className={`text-sm font-extrabold ${current || complete ? "text-vf-navy" : "text-slate-400"}`}>{item.label}</p>{current && <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-[0.08em] text-vf-primary">In progress</span>}</div><p className="mt-1 text-xs font-semibold">{item.detail}</p></div></div>; })}</div></div>
    </section>

    <div className="mt-5 grid gap-4 sm:grid-cols-2"><InfoCard icon={<Film className="h-5 w-5" />} label="Source video" value={incident?.video_metadata ? `${incident.video_metadata.width} × ${incident.video_metadata.height} · ${incident.video_metadata.duration.toFixed(1)}s` : "Loading video metadata…"} /><InfoCard icon={<Gauge className="h-5 w-5" />} label="Analysis passes" value={passLabel} /></div>
    {ready && <div className="mt-6 flex flex-col items-center justify-between gap-4 rounded-2xl border border-emerald-100 bg-emerald-50 p-5 sm:flex-row sm:px-6"><div><p className="font-extrabold text-emerald-900">Draft report ready</p><p className="mt-1 text-xs font-semibold text-emerald-700">Review the incident window, evidence and AI-generated report.</p></div><Link href={`/incidents/${id}`}><Button className="bg-emerald-600 hover:bg-emerald-700">Open review <ArrowRight className="h-4 w-4" /></Button></Link></div>}
  </div>;
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="section-card flex min-w-0 items-center gap-3 px-4 py-4"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-vf-primary">{icon}</span><span className="min-w-0"><span className="block text-[10px] font-extrabold uppercase tracking-[0.1em] text-slate-400">{label}</span><span className="mt-1 block truncate text-xs font-extrabold text-vf-navy">{value}</span></span></div>;
}

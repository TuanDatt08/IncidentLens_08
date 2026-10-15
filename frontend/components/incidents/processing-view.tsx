"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { ApiError, apiRequest, isSessionReady } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import { PipelineDetails, type PipelineDiagnostics } from "./pipeline-details";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, CircleAlert, Film, Gauge } from "@/components/icons";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { analyzeIncident, clearStoredJobId, getAnalysisJob, getStoredJobId } from "@/services/analysis.service";
import { getEvidence } from "@/services/evidence.service";
import { getIncident } from "@/services/incident.service";
import { getIncidentReport } from "@/services/report.service";
import type { IncidentRecord } from "@/types/incident";
import type { AnalysisJob, JobStatus, ProcessingStage } from "@/types/processing";

import { AnalysisProgress } from "./analysis-progress";

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
  const [diagnostics, setDiagnostics] = useState<PipelineDiagnostics>();
  const { status, can } = useAuth();
  const canAnalyze = can("analysis:create");
  const [incident, setIncident] = useState<IncidentRecord>();
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState<JobStatus>("queued");
  const [lastPass, setLastPass] = useState<1 | 2 | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressKnown, setProgressKnown] = useState(false);
  const [stage, setStage] = useState<ProcessingStage>("QUEUED");
  const [message, setMessage] = useState("Preparing analysis package.");
  const [ready, setReady] = useState(false);
  const [incidentDetected, setIncidentDetected] = useState<boolean>();
  const [error, setError] = useState("");
  const [outputErrors, setOutputErrors] = useState<{ report?: string; evidence?: string }>({});
  const [outputLoading, setOutputLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const startAnalysis = useRef<() => void>(() => undefined);
  const loadedOutputs = useRef({ report: false, evidence: false });
  const outputLoadInFlight = useRef(false);
  const retryOutputs = useRef<() => void>(() => undefined);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let snapshot: IncidentRecord | undefined;
    let creating = false;
    let trackingJob = false;
    setIncident(undefined); setJobId(""); setJobStatus("queued"); setLastPass(null);
    setProgress(0); setProgressKnown(false); setStage("QUEUED"); setError(""); setLoading(true); setStarting(false);
    setMessage("Loading incident status.");
    loadedOutputs.current = { report: false, evidence: false };
    outputLoadInFlight.current = false;
    setReady(false);
    setIncidentDetected(undefined);
    setOutputErrors({});
    setOutputLoading(false);

    async function loadOutputs() {
      if (outputLoadInFlight.current) return;
      const needsReport = !loadedOutputs.current.report;
      const needsEvidence = !loadedOutputs.current.evidence;
      if (!needsReport && !needsEvidence) return;
      outputLoadInFlight.current = true;
      setOutputLoading(true);
      setMessage("Analysis complete. Loading report and evidence.");
      const requests: Promise<void>[] = [];
      if (needsReport) requests.push(getIncidentReport(id).then((report) => {
        if (!active) return;
        loadedOutputs.current.report = true;
        setIncidentDetected(report.incident_detected);
        setOutputErrors((current) => ({ ...current, report: undefined }));
      }).catch((reason: unknown) => {
        if (active) setOutputErrors((current) => ({ ...current, report: reason instanceof Error ? reason.message : "Draft report could not be loaded." }));
      }));
      if (needsEvidence) requests.push(getEvidence(id).then(() => {
        if (!active) return;
        loadedOutputs.current.evidence = true;
        setOutputErrors((current) => ({ ...current, evidence: undefined }));
      }).catch((reason: unknown) => {
        if (active) setOutputErrors((current) => ({ ...current, evidence: reason instanceof Error ? reason.message : "Evidence could not be loaded." }));
      }));
      await Promise.all(requests);
      if (active && loadedOutputs.current.report && loadedOutputs.current.evidence) {
        setReady(true);
        setOutputErrors({});
        setMessage("Analysis complete. Draft report and evidence are ready to review.");
      } else if (active) {
        setMessage("Analysis completed. Retry loading the remaining review data.");
      }
      if (active) {
        outputLoadInFlight.current = false;
        setOutputLoading(false);
      }
    }
    retryOutputs.current = () => { void loadOutputs(); };
    let diagnosticsInFlight = false;
    let diagnosticsJob = "";
    async function readDiagnostics(currentJobId: string) {
      if (diagnosticsJob !== currentJobId) { diagnosticsJob = currentJobId; setDiagnostics(undefined); }
      if (USE_MOCK_API || diagnosticsInFlight || !active) return;
      diagnosticsInFlight = true;
      try {
        const details = await apiRequest<PipelineDiagnostics>(`/jobs/${encodeURIComponent(currentJobId)}/diagnostics`);
        if (active && diagnosticsJob === currentJobId) setDiagnostics(details);
      } catch { /* Optional diagnostics cannot delay or fail status polling. */ }
      finally { diagnosticsInFlight = false; }
    }

    async function poll(currentJobId: string) {
      if (!active || !isSessionReady()) return;
      let terminal = false;
      try {
        const job = await getAnalysisJob(currentJobId);
        void readDiagnostics(currentJobId);
        if (!active) return;
        setError("");
        setJobStatus(job.status);
        setLastPass(job.pass);
        setStage(jobStage(job));
        const known = job.status === "succeeded" || job.status !== "queued" && (job.pass === 1 || job.pass === 2) && Number.isFinite(job.progress.done) && Number.isFinite(job.progress.total) && job.progress.total !== null && job.progress.total > 0;
        setProgressKnown(known);
        setProgress(jobProgress(job));
        setMessage(jobMessage(job));

        if (job.status === "succeeded") {
          terminal = true;
          trackingJob = false;
          if (snapshot) { snapshot = { ...snapshot, processing_status: "COMPLETED" }; setIncident(snapshot); }
          clearStoredJobId(id);
          await loadOutputs();
          return;
        }
        if (job.status === "failed" || job.status === "cancelled") {
          terminal = true;
          trackingJob = false;
          if (snapshot) { snapshot = { ...snapshot, processing_status: "FAILED" }; setIncident(snapshot); }
          clearStoredJobId(id);
          setError(jobMessage(job));
          return;
        }
        timer = setTimeout(() => void poll(currentJobId), POLL_INTERVAL_MS);
      } catch (reason) {
        if (active) {
          if (reason instanceof ApiError && reason.status === 404) {
            trackingJob = false;
            clearStoredJobId(id); setJobId("");
            await loadIncident();
            return;
          }
          setError(reason instanceof Error ? reason.message : "Analysis status could not be loaded.");
          if (!terminal && !(reason instanceof ApiError && (reason.status === 401 || reason.status === 403))) timer = setTimeout(() => void poll(currentJobId), POLL_INTERVAL_MS);
        }
      }
    }

    async function loadIncident() {
      if (!active || !isSessionReady()) return;
      try {
        const data = await getIncident(id);
        if (!active) return;
        snapshot = data;
        setIncident(data);
        setError("");
        if (data.processing_status === "COMPLETED") {
          clearStoredJobId(id);
          setJobStatus("succeeded");
          setStage("COMPLETED");
          setProgress(100); setProgressKnown(true);
          await loadOutputs();
          return;
        }
        const latest = !USE_MOCK_API ? await apiRequest<{ job_id: string | null }>(`/incidents/${encodeURIComponent(id)}/latest-job`) : null;
        if (!active) return;
        const storedJobId = getStoredJobId(id) ?? latest?.job_id;
        if (storedJobId) {
          trackingJob = true;
          setJobId(storedJobId);
          await poll(storedJobId);
          return;
        }
        if (data.processing_status === "PROCESSING") {
          setJobStatus("running"); setStage("RUNNING"); setProgressKnown(false);
          setMessage("Analysis is already running. Tracking incident status; job details are unavailable in this tab.");
          timer = setTimeout(() => void loadIncident(), POLL_INTERVAL_MS);
        } else if (data.processing_status === "FAILED") {
          setJobStatus("failed"); setStage("FAILED");
          setMessage("Analysis failed. An Engineer can retry when ready.");
        } else {
          setMessage("Analysis has not started. An Engineer can choose Start analysis.");
        }
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Incident status could not be loaded.");
          if (snapshot?.processing_status === "PROCESSING" && !(reason instanceof ApiError && (reason.status === 401 || reason.status === 403))) timer = setTimeout(() => void loadIncident(), POLL_INTERVAL_MS);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    startAnalysis.current = () => {
      if (!active || !isSessionReady() || !canAnalyze || !snapshot || creating || trackingJob || snapshot.processing_status === "PROCESSING" || snapshot.processing_status === "COMPLETED") return;
      creating = true; setStarting(true); setError(""); setProgress(0); setProgressKnown(false);
      void analyzeIncident(id).then(async (accepted) => {
        if (!active) return;
        trackingJob = true;
        setJobId(accepted.job_id);
        await poll(accepted.job_id);
      }).catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Analysis could not be started.");
      }).finally(() => {
        creating = false;
        if (active) setStarting(false);
      });
    };
    void loadIncident();
    return () => {
      active = false;
      if (timer !== undefined) clearTimeout(timer);
      outputLoadInFlight.current = false;
      retryOutputs.current = () => undefined;
      startAnalysis.current = () => undefined;
    };
  }, [id, status, canAnalyze, refreshVersion]);

  const activeStageIndex = useMemo(() => {
    if (stage === "FAILED" || stage === "CANCELLED") return lastPass === 2 ? 3 : lastPass === 1 ? 2 : 1;
    return stages.findIndex((item) => item.key === stage);
  }, [stage, lastPass]);
  const idle = !jobId && incident?.processing_status !== "PROCESSING" && jobStatus === "queued";
  const statusLabel = idle ? "Not started" : jobStatus === "succeeded" ? "Completed" : jobStatus === "running" ? "Running" : jobStatus === "failed" ? "Failed" : jobStatus === "cancelled" ? "Cancelled" : "Queued";
  const statusStyle = jobStatus === "succeeded" ? "bg-emerald-50 text-emerald-700" : jobStatus === "failed" || jobStatus === "cancelled" ? "bg-red-50 text-red-700" : "bg-blue-50 text-blue-700";
  const passLabel = stage === "PASS_2" ? "Pass 2 active" : stage === "PASS_1" ? "Pass 1 active" : jobStatus === "succeeded" ? "Both passes complete" : "Waiting for pass 1";

  return <div className="analysis-workspace task-page mx-auto max-w-[980px]">
    <Link href="/incidents" className="mb-5 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link>
    <PageHeader title="Incident analysis" context={incident?.incident_id} description="Start analysis, follow progress, then open the draft to check evidence." action={incident && <span className={`inline-flex items-center rounded-md px-3 py-1.5 text-xs font-medium ${statusStyle}`}>{statusLabel}</span>} />
    {loading && <p role="status" className="mb-5 text-sm text-slate-600">Loading incident status…</p>}
    <div className="mb-5 flex flex-wrap gap-3">
      {canAnalyze && incident && !loading && incident.processing_status !== "PROCESSING" && incident.processing_status !== "COMPLETED" && (idle || jobStatus === "failed" || jobStatus === "cancelled") && <Button disabled={starting} onClick={() => startAnalysis.current()}>{starting ? "Starting…" : idle ? "Start analysis" : "Retry analysis"}</Button>}
      {error && <Button variant="ghost" disabled={starting || loading} onClick={() => setRefreshVersion((version) => version + 1)}>Refresh status</Button>}
    </div>

    {error && <div role="alert" className="mb-5 flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
    {(outputErrors.report || outputErrors.evidence) && <div role="alert" className="mb-5 rounded-xl border border-red-100 bg-red-50 px-4 py-4 text-sm text-red-800"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><p className="font-extrabold">Analysis completed, but some review data could not be loaded.</p>{outputErrors.report && <p className="mt-1">Draft report: {outputErrors.report}</p>}{outputErrors.evidence && <p className="mt-1">Evidence: {outputErrors.evidence}</p>}</div><Button variant="ghost" disabled={outputLoading} onClick={() => retryOutputs.current()}>{outputLoading ? "Retrying…" : "Retry failed loads"}</Button></div></div>}
    {outputLoading && <p role="status" className="mb-5 text-sm font-semibold text-slate-600">Analysis is complete. Loading report and evidence…</p>}

    <section className="section-card overflow-hidden">
      <div className="analysis-progress-panel px-5 py-6 sm:px-8"><p className="mb-2 break-all text-xs text-slate-500">AI pipeline{jobId ? ` / ${jobId}` : ""}</p><h2 className="mb-4 text-sm font-medium leading-6 text-vf-navy">{message}</h2><AnalysisProgress key={`${id}:${jobId}`} value={progressKnown ? progress : null} state={idle ? "idle" : jobStatus} paused={!!error || status !== "authenticated"} /></div>
      <div className="p-5 sm:p-8"><div className="space-y-0">{stages.map((item, index) => { const complete = index < activeStageIndex || ready; const current = index === activeStageIndex && !ready && !idle && (jobStatus === "queued" || jobStatus === "running"); return <div key={item.key} className="flex gap-4"><div className="flex flex-col items-center"><span className={`z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-4 border-white text-xs font-extrabold ${complete ? "bg-vf-primary text-white" : current ? "bg-blue-50 text-vf-primary ring-4 ring-blue-50" : "bg-slate-100 text-slate-400"}`}>{complete ? <Check className="h-4 w-4" /> : index + 1}</span>{index < stages.length - 1 && <span className={`w-0.5 flex-1 ${complete ? "bg-blue-200" : "bg-slate-100"}`} />}</div><div className={`min-h-[68px] pb-5 ${current ? "text-vf-navy" : "text-slate-500"}`}><div className="flex flex-wrap items-center gap-2"><p className={`text-sm font-extrabold ${current || complete ? "text-vf-navy" : "text-slate-400"}`}>{item.label}</p>{current && <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-[0.08em] text-vf-primary">In progress</span>}</div><p className="mt-1 text-xs font-semibold">{item.detail}</p></div></div>; })}</div></div>
    </section>

    {diagnostics && <details className="section-card mt-5 p-5"><summary className="cursor-pointer text-sm font-semibold text-vf-navy">Processing details</summary><div className="mt-4"><PipelineDetails data={diagnostics} /></div></details>}
    <div className="mt-5 grid gap-4 sm:grid-cols-2"><InfoCard icon={<Film className="h-5 w-5" />} label="Source video" value={incident?.video_metadata ? `${incident.video_metadata.width} × ${incident.video_metadata.height} · ${incident.video_metadata.duration.toFixed(1)}s` : "Loading video metadata…"} /><InfoCard icon={<Gauge className="h-5 w-5" />} label="Analysis passes" value={passLabel} /></div>
    {ready && <div className={`mt-6 flex flex-col items-center justify-between gap-4 rounded-2xl border p-5 sm:flex-row sm:px-6 ${incidentDetected === false ? "border-amber-200 bg-amber-50" : "border-emerald-100 bg-emerald-50"}`}><div><p className={`font-extrabold ${incidentDetected === false ? "text-amber-950" : "text-emerald-900"}`}>{incidentDetected === false ? "Analysis needs review: no incident confirmed" : "Draft report ready"}</p><p className={`mt-1 text-xs font-semibold ${incidentDetected === false ? "text-amber-900" : "text-emerald-700"}`}>{incidentDetected === false ? "Open review to check telemetry conflicts, unresolved observations and coverage limits." : "Review the incident window, evidence and AI-generated report."}</p></div><Link href={`/incidents/${id}`} className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-vf-primary px-4 text-sm font-semibold text-white hover:bg-teal-800">Open review <ArrowRight className="h-4 w-4" /></Link></div>}
  </div>;
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="section-card flex min-w-0 items-center gap-3 px-4 py-4"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-vf-primary">{icon}</span><span className="min-w-0"><span className="block text-[10px] font-extrabold uppercase tracking-[0.1em] text-slate-400">{label}</span><span className="mt-1 block truncate text-xs font-extrabold text-vf-navy">{value}</span></span></div>;
}

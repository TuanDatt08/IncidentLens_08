"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import { analyzeIncident, clearStoredJobId, getAnalysisJob, getStoredJobId } from "@/services/analysis.service";
import { getIncident } from "@/services/incident.service";
import type { IncidentRecord } from "@/types/incident";
import { PipelineDetails, type PipelineDiagnostics } from "./pipeline-details";

export function ProcessingView({ id }: { id: string }) {
  const [incident, setIncident] = useState<IncidentRecord>();
  const [diagnostics, setDiagnostics] = useState<PipelineDiagnostics>();
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("queued");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll(currentId: string) {
      try {
        const job = await getAnalysisJob(currentId);
        if (!active) return;
        setStatus(job.status);
        if (!USE_MOCK_API) {
          const data = await apiRequest<PipelineDiagnostics>(`/jobs/${encodeURIComponent(currentId)}/diagnostics`);
          if (!active) return;
          setDiagnostics(data);
        }
        setError(job.error?.message ?? "");
        if (job.status === "queued" || job.status === "running") timer = setTimeout(() => void poll(currentId), 2000);
      } catch (cause) {
        if (active) { setError(cause instanceof Error ? cause.message : "Không đọc được trạng thái backend."); timer = setTimeout(() => void poll(currentId), 4000); }
      }
    }
    async function start() {
      try {
        const data = await getIncident(id);
        if (!active) return;
        setIncident(data);
        const stored = getStoredJobId(id);
        const latest = !USE_MOCK_API && attempt === 0 ? await apiRequest<{job_id: string | null}>(`/incidents/${encodeURIComponent(id)}/latest-job`) : null;
        if (data.processing_status === "COMPLETED" && !stored && !latest?.job_id) { setStatus("succeeded"); return; }
        const currentId = stored ?? latest?.job_id ?? (await analyzeIncident(id)).job_id;
        if (!active) return;
        setJobId(currentId);
        await poll(currentId);
      } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : "Không khởi động được phân tích."); }
    }
    void start();
    return () => { active = false; clearTimeout(timer); };
  }, [id, attempt]);
  function retry() { clearStoredJobId(id); setError(""); setDiagnostics(undefined); setStatus("queued"); setAttempt(value => value + 1); }
  return <div className="mx-auto max-w-[980px]">
    <Link href="/incidents" className="mb-6 inline-block text-sm font-bold text-slate-500">← Danh sách incident</Link>
    <div className="mb-6"><p className="eyebrow">{id}</p><h1 className="mt-2 text-3xl font-extrabold text-vf-navy">Luồng phân tích video</h1><p className="mt-2 text-sm text-slate-600">Upload đã hoàn tất. Theo dõi backend, prompt, Qwen và lưu database tại đây.</p><p className="mt-2 break-all text-xs text-slate-500">{jobId} · {incident?.video_metadata?.duration.toFixed(2)} giây · {status}</p></div>
    {error && <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{diagnostics?.error_code ? `${diagnostics.error_code}: ` : ""}{diagnostics?.stage === "error" ? diagnostics.message : error}</div>}
    {diagnostics ? <PipelineDetails data={diagnostics} /> : <section className="section-card p-6" role="status">{status === "succeeded" ? "Draft đã lưu vào database." : "Backend đang tiếp nhận job. Đang tải trạng thái thực…"}</section>}
    {(status === "failed" || status === "cancelled") && <Button className="mt-5" onClick={retry}>Chạy lại sau khi sửa cấu hình</Button>}
    {status === "succeeded" && <div className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-xl bg-emerald-50 p-5"><p className="font-bold text-emerald-900">DRAFT đã lưu. Kỹ sư cần kiểm tra evidence và các giới hạn.</p><Link href={`/incidents/${id}`}><Button>Mở review</Button></Link></div>}
  </div>;
}

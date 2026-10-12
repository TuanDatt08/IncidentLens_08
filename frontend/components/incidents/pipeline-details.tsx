"use client";

import { useEffect, useState } from "react";

export type PipelineDiagnostics = {
  stage: string;
  at?: string;
  message: string;
  model?: string;
  prompt_path?: string;
  prompt_sha256?: string;
  prompt_text?: string;
  request_id?: string;
  frame_times_s?: number[];
  error_code?: string;
  alignment?: { quality: string; unknowns?: string[] };
  events: { stage: string; message: string; at: string; request_id?: string }[];
  result?: unknown;
};

const labels: Record<string, string> = { backend: "Backend", prompt: "Prompt", qwen: "Model Qwen 7B", validation: "Kiểm tra output", database: "Database", complete: "DRAFT chờ review", error: "Lỗi xử lý" };

export function PipelineDetails({ data }: { data: PipelineDiagnostics }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const elapsed = data.at ? Math.max(0, Math.floor((now - new Date(data.at).getTime()) / 1000)) : 0;
  return <section className="section-card space-y-5 p-5 sm:p-8">
    <div aria-live="polite"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Bước hiện tại</p><h2 className="mt-1 text-xl font-extrabold text-vf-navy">{labels[data.stage] ?? data.stage}</h2><p className="mt-2 text-sm text-slate-700">{data.message}</p></div>
    {data.stage === 'qwen' && <p className="text-sm text-slate-500">Đang chờ phản hồi: {Math.floor(elapsed / 60)} phút {elapsed % 60} giây. CPU có thể mất nhiều phút cho mỗi lượt.</p>}
    {data.alignment && <p className={`rounded-lg p-3 text-sm ${data.alignment.quality === "VERIFIED" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>Đồng bộ CSV/video: {data.alignment.quality}. {data.alignment.unknowns?.join(" ")}</p>}
    <dl className="grid gap-4 text-sm sm:grid-cols-2">{[["Model", data.model], ["Request", data.request_id], ["Prompt", data.prompt_path], ["Frame (giây)", data.frame_times_s?.join(", ")], ["Mã lỗi", data.error_code]].filter(([,value]) => value).map(([label,value]) => <div key={label}><dt className="font-bold text-slate-500">{label}</dt><dd className="mt-1 break-all text-vf-navy">{value}</dd></div>)}</dl>
    {data.prompt_text && <details className="rounded-lg border border-slate-200 p-3"><summary className="cursor-pointer font-bold text-vf-navy">Prompt thực đang sử dụng</summary><p className="my-3 break-all text-xs text-slate-500">SHA-256: {data.prompt_sha256}</p><pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs leading-5">{data.prompt_text}</pre></details>}
    <details className="rounded-lg border border-slate-200 p-3"><summary className="cursor-pointer font-bold text-vf-navy">Lịch sử xử lý ({data.events.length} bước)</summary><ol className="mt-4 space-y-3">{data.events.map((event,index) => <li key={`${event.at}-${index}`} className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">{new Date(event.at).toLocaleTimeString("vi-VN")} · {labels[event.stage] ?? event.stage}</p><p className="mt-1 text-sm">{event.message}</p></li>)}</ol></details>
    {data.result !== undefined && data.result !== null && <details className="rounded-lg border border-slate-200 p-3"><summary className="cursor-pointer font-bold text-vf-navy">Output đầy đủ Stage A / Stage B</summary><pre className="mt-4 max-h-[600px] overflow-auto whitespace-pre-wrap break-words text-xs leading-5">{JSON.stringify(data.result, null, 2)}</pre></details>}
  </section>;
}

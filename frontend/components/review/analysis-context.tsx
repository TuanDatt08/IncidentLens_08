"use client";

import { createContext, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, apiRequest } from "@/lib/api-client";
import { AUTH_ENABLED, USE_MOCK_API } from "@/lib/config";
import { Button } from "@/components/ui/button";
import { StructuredAnalysis, asRecord } from "./structured-analysis";

type Point = { time_s: number; speed_kmh: number | null; brake_pct: number | null; acceleration: number | null };
export type ReviewContext = {
  review_required: boolean; detection_state: string | null; summary: string | null;
  primary_analysis?: Record<string, unknown> | null; analyses?: Record<string, unknown>[];
  model_output: Record<string, unknown>; warnings: string[]; time_basis: string;
  alignment: string; points: Point[]; windows: number[][]; telemetry_error: string | null;
};

type Resource = { id: string; data?: ReviewContext; error: string; accessError: boolean; retry: () => void };
const AnalysisResourceContext = createContext<Resource | null>(null);
function useAnalysisResource(id: string, enabled: boolean): Resource {
  const [data, setData] = useState<ReviewContext>();
  const [error, setError] = useState("");
  const [accessError, setAccessError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setData(undefined); setError(""); setAccessError(false);
    if (USE_MOCK_API || !enabled) return;
    apiRequest<ReviewContext>(`/incidents/${encodeURIComponent(id)}/review-context`)
      .then(value => { if (active) { setData(value); } })
      .catch((cause: Error) => { if (active) { setError(cause.message); setAccessError(cause instanceof ApiError && (cause.status === 401 || cause.status === 403)); } });
    return () => { active = false; };
  }, [id, attempt, enabled]);
  return { id, data, error, accessError, retry: () => setAttempt(value => value + 1) };
}
export function AnalysisContextProvider({ id, children }: { id: string; children: React.ReactNode }) {
  const resource = useAnalysisResource(id, true);
  return <AnalysisResourceContext.Provider value={resource}>{children}</AnalysisResourceContext.Provider>;
}

export function AnalysisContext({ id, onSeek, currentTime = 0, seekEnabled = true, mode = "all" }: { mode?: "all" | "telemetry" | "analysis"; id: string; onSeek: (time: number) => void; currentTime?: number; seekEnabled?: boolean }) {
  const shared = useContext(AnalysisResourceContext);
  const fallback = useAnalysisResource(id, !shared || shared.id !== id);
  const { data, error, accessError, retry } = shared?.id === id ? shared : fallback;
  const [cursor, setCursor] = useState(0);
  const [analysisIndex, setAnalysisIndex] = useState(0);
  useEffect(() => { setAnalysisIndex(0); }, [id]);
  useEffect(() => {
    const index = data?.analyses?.findIndex(item => item.analysis_status === "CONFIRMED") ?? -1;
    setAnalysisIndex(index >= 0 ? index : 0);
  }, [data]);
  useEffect(() => {
    if (!data?.points.length) return;
    setCursor(data.points.reduce((best, point, index) => Math.abs(point.time_s - currentTime) < Math.abs(data.points[best].time_s - currentTime) ? index : best, 0));
  }, [currentTime, data]);
  if (USE_MOCK_API) return null;
  // Shared loading and failure state belongs to one surface, not both modes.
  if ((!data || error) && mode === "analysis" && shared) return null;
  if (error) return <section lang="vi" className="section-card p-5"><h2 className="font-semibold text-vf-navy">Output AI và telemetry</h2><p role="alert" className="mt-2 text-sm text-red-700">{accessError ? "Chưa có phiên đăng nhập hợp lệ hoặc tài khoản chưa được cấp quyền đọc dữ liệu bổ sung." : `Không tải được dữ liệu bổ sung: ${error}`}</p>{accessError && <p className="mt-2 text-sm text-slate-600">{AUTH_ENABLED ? "Đăng nhập bằng tài khoản có quyền đọc sự cố, sau đó thử lại." : "Workspace chưa bật đăng nhập. Quản trị viên cần đồng bộ cấu hình xác thực frontend và backend trước khi truy cập."}</p>}{accessError && AUTH_ENABLED ? <Link href={`/login?returnTo=${encodeURIComponent(`/incidents/${id}`)}`} className="mt-4 inline-flex min-h-11 items-center font-semibold underline">Đăng nhập</Link> : !accessError && <Button variant="secondary" className="mt-4" onClick={retry}>Thử lại</Button>}</section>;
  if (!data) return <p lang="vi" className="text-sm text-slate-600" role="status">Đang tải output Qwen và telemetry…</p>;
  const point = data.points[Math.min(cursor, data.points.length - 1)];
  const primary = asRecord(data.primary_analysis), legacy = asRecord(data.model_output.analysis);
  const analysis = data.analyses?.[analysisIndex] || (Object.keys(primary).length ? primary : Object.keys(legacy).length ? legacy : data.model_output);
  const showAnalysis = mode !== "telemetry", showTelemetry = mode !== "analysis";
  const chooseTime = (index: number) => {
    setCursor(index);
    if (seekEnabled && data.points[index]) onSeek(data.points[index].time_s);
  };
  return <section lang="vi" className="section-card p-5 sm:p-6" aria-label={mode === "telemetry" ? "Telemetry đồng bộ" : "Phân tích sự cố"}>
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold text-vf-navy">{mode === "telemetry" ? "Telemetry đồng bộ" : "Phân tích sự cố"}</h2><span className="text-xs text-slate-600">Giây từ đầu video gốc</span></div>
    {showAnalysis && data.review_required && <div role="note" className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950"><p className="font-bold">Cần kỹ sư review — kết luận AI chưa giải quyết được nguy cơ</p><p className="mt-1 text-sm leading-6">Qwen trả âm tính nhưng telemetry có dấu hiệu phanh khẩn cấp. Đây không phải xác nhận “không có incident”. Output vẫn được giữ bên dưới và cần được đối chiếu với evidence.</p></div>}
    {showAnalysis && <>
    {data.analyses && data.analyses.length > 1 && <label className="mt-4 block text-xs font-semibold text-slate-600">Chọn sự kiện được phân tích<select value={analysisIndex} onChange={event => setAnalysisIndex(Number(event.target.value))} className="mt-2 block w-full rounded-lg border border-slate-300 bg-transparent p-3 text-sm text-vf-navy">{data.analyses.map((item, index) => <option key={index} value={index}>{typeof item.incident_id === "string" ? item.incident_id : `Sự kiện ${index + 1}`}</option>)}</select></label>}
    {data.warnings?.length > 0 && <ul className="mt-4 space-y-2 text-sm text-amber-700" aria-label="Cảnh báo dữ liệu">{data.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
    <StructuredAnalysis analysis={{ ...analysis, summary: analysis.summary ?? data.summary }} onSeek={onSeek} seekEnabled={seekEnabled} />
    <details className="mt-4 border-t border-slate-200 pt-3"><summary className="cursor-pointer text-sm font-semibold text-vf-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4">Xem JSON output đã lưu</summary><pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">{JSON.stringify(data.analyses?.length ? data.analyses : data.model_output, null, 2)}</pre></details>
    </>}
    {showTelemetry && <>{data.points.length > 1 ? <div className="mt-7 border-t border-slate-200 pt-5">
      <h3 className="font-bold text-vf-navy">Diễn biến tốc độ và phanh</h3><p className="mt-1 text-sm leading-6 text-slate-600">Vùng được tô nền là khoảng cần kiểm tra. Hai biểu đồ dùng cùng đồng hồ video; mỗi tín hiệu có đơn vị riêng.</p>
      <p className="mt-2 text-sm tabular-nums text-slate-700">Tốc độ đầu / cuối khoảng hiển thị: {data.points[0].speed_kmh?.toFixed(1) ?? "—"} / {data.points[data.points.length - 1].speed_kmh?.toFixed(1) ?? "—"} km/h; phanh lớn nhất {Math.max(...data.points.map(p => p.brake_pct ?? 0)).toFixed(1)}%.</p>
      <div className="review-signal-stack mt-4 grid gap-5"><SignalChart title="Speed" unit="km/h" field="speed_kmh" color="var(--workspace-link, #78edff)" points={data.points} windows={data.windows} cursor={Math.min(cursor, data.points.length - 1)} setCursor={chooseTime} /><SignalChart title="Brake" unit="%" field="brake_pct" color="var(--workspace-signal-secondary, #c4a5ff)" points={data.points} windows={data.windows} cursor={Math.min(cursor, data.points.length - 1)} setCursor={chooseTime} /></div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm tabular-nums"><p><strong>{point.time_s.toFixed(3)}s</strong> · Tốc độ <strong>{point.speed_kmh?.toFixed(1) ?? "—"} km/h</strong> · Phanh <strong>{point.brake_pct?.toFixed(1) ?? "—"}%</strong> · Gia tốc <strong>{point.acceleration?.toFixed(2) ?? "—"} m/s²</strong></p><button type="button" disabled={!seekEnabled} onClick={() => onSeek(point.time_s)} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold text-vf-primary hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2">Xem video tại {point.time_s.toFixed(2)}s</button></div>
      <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="telemetry-cursor">Chọn thời điểm trên biểu đồ</label><input id="telemetry-cursor" aria-valuetext={`${point.time_s.toFixed(3)} giây, tốc độ ${point.speed_kmh?.toFixed(1) ?? 'không có'} km/h, phanh ${point.brake_pct?.toFixed(1) ?? 'không có'} phần trăm`} className="mt-2 w-full accent-blue-600" type="range" min={0} max={data.points.length - 1} value={cursor} onChange={e => chooseTime(Number(e.target.value))} />
      <p className="mt-2 text-xs text-slate-600">Dữ liệu CSV đã đồng bộ: {data.alignment}. Có thể giảm số điểm vẽ, giữ cực trị để không mất đỉnh phanh.</p>
    </div> : <p className="mt-5 text-sm text-slate-600">{data.telemetry_error || "No synchronized telemetry is available for this recording."}</p>}
    </>}
    {showAnalysis && <p className="review-coverage-note">Phân tích chỉ bao phủ dữ liệu đã cung cấp. Sự việc chưa quan sát và nguyên nhân chưa được kiểm chứng vẫn chưa xác định; cần kỹ sư đối chiếu bằng chứng trước khi duyệt.</p>}
  </section>;
}

function SignalChart({ title, unit, field, color, points, windows, cursor, setCursor }: { title: string; unit: string; field: "speed_kmh" | "brake_pct"; color: string; points: Point[]; windows: number[][]; cursor: number; setCursor: (index: number) => void }) {
  const start = points[0].time_s, span = Math.max(.001, points[points.length - 1].time_s - start);
  const max = field === "brake_pct" ? 100 : Math.max(10, Math.ceil(Math.max(...points.map(p => p[field] ?? 0)) / 10) * 10);
  const x = (time: number) => 54 + (time - start) / span * 500;
  const y = (value: number) => 148 - value / max * 112;
  let path = "", connected = false;
  for (const point of points) { const value = point[field]; if (value === null) { connected = false; continue; } path += `${connected ? "L" : "M"}${x(point.time_s).toFixed(2)},${y(value).toFixed(2)} `; connected = true; }
  return <div><h4 className="text-sm font-bold" style={{ color }}>{title} <span className="font-normal">({unit})</span></h4><svg viewBox="0 0 580 180" className="mt-2 w-full" role="img" aria-label={`${title} theo giây video. Dùng thanh chọn thời điểm bên dưới để đọc giá trị.`} onClick={e => { const rect = e.currentTarget.getBoundingClientRect(); const time = start + Math.max(0, Math.min(1, ((e.clientX - rect.left) / rect.width * 580 - 54) / 500)) * span; setCursor(points.reduce((best, p, i) => Math.abs(p.time_s - time) < Math.abs(points[best].time_s - time) ? i : best, 0)); }}>
    <title>{title} ({unit})</title>
    {windows.map((w, i) => <rect key={i} x={x(Math.max(start, w[0]))} y={36} width={Math.max(0, x(Math.min(start + span, w[1])) - x(Math.max(start, w[0])))} height={112} fill="var(--workspace-primary-soft)" />)}
    {[0, max / 2, max].map(value => <g key={value}><line x1={54} x2={554} y1={y(value)} y2={y(value)} stroke="var(--workspace-border)" /><text x={44} y={y(value) + 4} textAnchor="end" fontSize={14} className="text-[24px] sm:text-[14px]" fill="var(--workspace-muted)">{value}</text></g>)}
    <path d={path} fill="none" stroke={color} strokeWidth={2.5} /><line x1={x(points[cursor].time_s)} x2={x(points[cursor].time_s)} y1={36} y2={148} stroke="var(--workspace-muted)" strokeDasharray="4 4" />
    {[start, start + span / 2, start + span].map(time => <text key={time} x={x(time)} y={170} textAnchor={time === start ? "start" : time === start + span ? "end" : "middle"} fontSize={14} className="text-[24px] sm:text-[14px]" fill="var(--workspace-muted)">{time.toFixed(2)}s</text>)}
  </svg></div>;
}

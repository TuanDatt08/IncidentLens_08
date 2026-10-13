"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";

type Point = { time_s: number; speed_kmh: number | null; brake_pct: number | null; acceleration: number | null };
export type ReviewContext = {
  review_required: boolean; detection_state: string | null; summary: string | null;
  model_output: Record<string, unknown>; warnings: string[]; time_basis: string;
  alignment: string; points: Point[]; windows: number[][]; telemetry_error: string | null;
};

export function AnalysisContext({ id, onSeek }: { id: string; onSeek: (time: number) => void }) {
  const [data, setData] = useState<ReviewContext>();
  const [error, setError] = useState("");
  const [cursor, setCursor] = useState(0);
  useEffect(() => {
    let active = true;
    setData(undefined); setError("");
    if (USE_MOCK_API) return;
    apiRequest<ReviewContext>(`/incidents/${encodeURIComponent(id)}/review-context`)
      .then(value => { if (active) { setData(value); setCursor(Math.max(0, value.points.findIndex(p => p.brake_pct === Math.max(...value.points.map(p => p.brake_pct ?? 0))))); } })
      .catch((cause: Error) => { if (active) setError(cause.message); });
    return () => { active = false; };
  }, [id]);
  if (USE_MOCK_API) return null;
  if (error) return <section className="section-card p-5" role="status"><h2 className="font-bold text-vf-navy">Output AI và telemetry</h2><p className="mt-2 text-sm text-red-700">Không tải được dữ liệu bổ sung: {error}</p></section>;
  if (!data) return <p className="text-sm text-slate-600" role="status">Đang tải output Qwen và telemetry…</p>;
  const point = data.points[cursor];
  return <section className="section-card p-5 sm:p-6" aria-labelledby="analysis-context-title">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 id="analysis-context-title" className="text-xl font-bold text-vf-navy">Output AI và telemetry</h2><span className="text-xs font-semibold text-slate-600">Thời gian từ đầu video · giây</span></div>
    {data.review_required && <div role="note" className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950"><p className="font-bold">Cần kỹ sư review — kết luận AI chưa giải quyết được nguy cơ</p><p className="mt-1 text-sm leading-6">Qwen trả âm tính nhưng telemetry có dấu hiệu phanh khẩn cấp. Đây không phải xác nhận “không có incident”. Output vẫn được giữ bên dưới và cần được đối chiếu với evidence.</p></div>}
    <div className="mt-5"><h3 className="text-sm font-bold text-vf-navy">Kết quả tổng hợp Qwen</h3><p className="mt-2 max-w-prose whitespace-pre-line text-sm leading-6 text-slate-700">{data.summary || "Chưa có output tổng hợp để hiển thị."}</p></div>
    <details className="mt-4 border-t border-slate-200 pt-3"><summary className="cursor-pointer text-sm font-semibold text-vf-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4">Xem JSON output đã lưu</summary><pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">{JSON.stringify(data.model_output, null, 2)}</pre></details>
    {data.points.length > 1 ? <div className="mt-7 border-t border-slate-200 pt-5">
      <h3 className="font-bold text-vf-navy">Diễn biến tốc độ và phanh</h3><p className="mt-1 text-sm leading-6 text-slate-600">Vùng nền vàng là khoảng cần kiểm tra. Hai biểu đồ dùng cùng đồng hồ video; mỗi tín hiệu có đơn vị riêng.</p>
      <p className="mt-2 text-sm tabular-nums text-slate-700">Tốc độ đầu / cuối khoảng hiển thị: {data.points[0].speed_kmh?.toFixed(1) ?? "—"} / {data.points[data.points.length - 1].speed_kmh?.toFixed(1) ?? "—"} km/h; phanh lớn nhất {Math.max(...data.points.map(p => p.brake_pct ?? 0)).toFixed(1)}%.</p>
      <div className="mt-4 grid gap-6 lg:grid-cols-2"><SignalChart title="Tốc độ" unit="km/h" field="speed_kmh" color="#2563eb" points={data.points} windows={data.windows} cursor={cursor} setCursor={setCursor} /><SignalChart title="Phanh" unit="%" field="brake_pct" color="#b45309" points={data.points} windows={data.windows} cursor={cursor} setCursor={setCursor} /></div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm tabular-nums"><p><strong>{point.time_s.toFixed(3)}s</strong> · Tốc độ <strong>{point.speed_kmh?.toFixed(1) ?? "—"} km/h</strong> · Phanh <strong>{point.brake_pct?.toFixed(1) ?? "—"}%</strong> · Gia tốc <strong>{point.acceleration?.toFixed(2) ?? "—"} m/s²</strong></p><button type="button" onClick={() => onSeek(point.time_s)} className="rounded-lg border border-slate-300 px-3 py-2 font-semibold text-vf-primary hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2">Xem video tại {point.time_s.toFixed(2)}s</button></div>
      <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="telemetry-cursor">Chọn thời điểm trên biểu đồ</label><input id="telemetry-cursor" aria-valuetext={`${point.time_s.toFixed(3)} giây, tốc độ ${point.speed_kmh?.toFixed(1) ?? 'không có'} km/h, phanh ${point.brake_pct?.toFixed(1) ?? 'không có'} phần trăm`} className="mt-2 w-full accent-blue-600" type="range" min={0} max={data.points.length - 1} value={cursor} onChange={e => setCursor(Number(e.target.value))} />
      <p className="mt-2 text-xs text-slate-600">Dữ liệu CSV đã đồng bộ: {data.alignment}. Có thể giảm số điểm vẽ, giữ cực trị để không mất đỉnh phanh.</p>
    </div> : <p className="mt-5 text-sm text-amber-800">{data.telemetry_error || "Không đủ mẫu telemetry để vẽ biểu đồ."}</p>}
  </section>;
}

function SignalChart({ title, unit, field, color, points, windows, cursor, setCursor }: { title: string; unit: string; field: "speed_kmh" | "brake_pct"; color: string; points: Point[]; windows: number[][]; cursor: number; setCursor: (index: number) => void }) {
  const start = points[0].time_s, span = Math.max(.001, points[points.length - 1].time_s - start);
  const max = field === "brake_pct" ? 100 : Math.max(10, Math.ceil(Math.max(...points.map(p => p[field] ?? 0)) / 10) * 10);
  const x = (time: number) => 54 + (time - start) / span * 500;
  const y = (value: number) => 148 - value / max * 112;
  let path = "", connected = false;
  for (const point of points) { const value = point[field]; if (value === null) { connected = false; continue; } path += `${connected ? "L" : "M"}${x(point.time_s).toFixed(2)},${y(value).toFixed(2)} `; connected = true; }
  return <div><h4 className="text-sm font-bold" style={{ color }}>{title} <span className="font-normal">({unit})</span></h4><svg viewBox="0 0 580 180" className="mt-2 w-full" role="img" aria-label={`${title} theo giây video. Dùng thanh chọn thời điểm bên dưới để đọc giá trị.`} onPointerMove={e => { const rect = e.currentTarget.getBoundingClientRect(); const time = start + Math.max(0, Math.min(1, ((e.clientX - rect.left) / rect.width * 580 - 54) / 500)) * span; setCursor(points.reduce((best, p, i) => Math.abs(p.time_s - time) < Math.abs(points[best].time_s - time) ? i : best, 0)); }}>
    <title>{title} ({unit})</title>
    {windows.map((w, i) => <rect key={i} x={x(Math.max(start, w[0]))} y={36} width={Math.max(0, x(Math.min(start + span, w[1])) - x(Math.max(start, w[0])))} height={112} fill="#fef3c7" />)}
    {[0, max / 2, max].map(value => <g key={value}><line x1={54} x2={554} y1={y(value)} y2={y(value)} stroke="#cbd5e1" /><text x={44} y={y(value) + 4} textAnchor="end" fontSize={14} className="text-[24px] sm:text-[14px]" fill="#475569">{value}</text></g>)}
    <path d={path} fill="none" stroke={color} strokeWidth={2.5} /><line x1={x(points[cursor].time_s)} x2={x(points[cursor].time_s)} y1={36} y2={148} stroke="#334155" strokeDasharray="4 4" />
    {[start, start + span / 2, start + span].map(time => <text key={time} x={x(time)} y={170} textAnchor={time === start ? "start" : time === start + span ? "end" : "middle"} fontSize={14} className="text-[24px] sm:text-[14px]" fill="#475569">{time.toFixed(2)}s</text>)}
  </svg></div>;
}

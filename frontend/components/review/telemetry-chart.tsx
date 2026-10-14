"use client";

import { useState } from "react";
import type { TelemetryChart as TelemetryData } from "@/types/telemetry";

type Props = { data: TelemetryData; currentTime: number; seekEnabled: boolean; onSeek: (videoSeconds: number) => void; window?: { start_s: number; critical_s: number; end_s: number } | null; seekRange?: { start_s: number; end_s: number } };
const format = (value: number) => Number.isFinite(value) ? Number(value.toFixed(2)).toString() : "Unknown";

export function TelemetryChart({ data, currentTime, seekEnabled, onSeek, window, seekRange }: Props) {
  const [selected, setSelected] = useState("");
  const signals = data.signals.filter((signal) => signal.samples.some((sample) => Number.isFinite(sample.time_s) && sample.value !== null && Number.isFinite(sample.value)));
  const signal = signals.find((entry) => entry.key === selected) ?? signals[0];
  if (data.state !== "available" || !signal) return <section className="telemetry-chart section-card p-5 sm:p-6"><h2 className="text-lg font-semibold text-vf-navy">Telemetry</h2><p className="mt-3 text-sm text-slate-600">{data.message || "No telemetry data is available for this recording."}</p></section>;

  const samples = signal.samples.filter((sample) => Number.isFinite(sample.time_s)).slice().sort((a, b) => a.time_s - b.time_s);
  const values = samples.filter((sample) => sample.value !== null && Number.isFinite(sample.value)).map((sample) => sample.value!);
  const minTime = samples[0].time_s; const maxTime = samples[samples.length - 1].time_s;
  const timeSpan = maxTime - minTime || 1;
  let minValue = values.reduce((minimum, value) => Math.min(minimum, value), Infinity); let maxValue = values.reduce((maximum, value) => Math.max(maximum, value), -Infinity);
  if (minValue === maxValue) { const pad = Math.max(0.5, Math.abs(minValue) * 0.05); minValue -= pad; maxValue += pad; }
  const x = (time: number) => 55 + (time - minTime) / timeSpan * 649;
  const y = (value: number) => 16 + (maxValue - value) / (maxValue - minValue) * 134;
  const verified = data.time_basis === "video_seconds" && data.alignment === "VERIFIED";
  const validRange = !seekRange || Number.isFinite(seekRange.start_s) && Number.isFinite(seekRange.end_s) && seekRange.end_s >= seekRange.start_s;
  const limit = Math.min(data.duration_s !== null && Number.isFinite(data.duration_s) && data.duration_s >= 0 ? Math.min(maxTime, data.duration_s) : maxTime, validRange && seekRange ? seekRange.end_s : Infinity);
  const seekMin = Math.max(0, minTime, validRange && seekRange ? seekRange.start_s : -Infinity);
  const canSeek = verified && seekEnabled && validRange && limit > seekMin;
  const cursorVisible = verified && seekEnabled && Number.isFinite(currentTime) && currentTime >= minTime && currentTime <= maxTime;
  const preceding = cursorVisible ? samples.filter((sample) => sample.time_s <= currentTime).at(-1) : undefined;
  const currentSample = preceding && preceding.value !== null && Number.isFinite(preceding.value) ? preceding : undefined;
  let connected = false;
  const path = samples.map((sample) => {
    if (sample.value === null || !Number.isFinite(sample.value)) { connected = false; return ""; }
    const command = connected ? "L" : "M"; connected = true;
    return `${command}${x(sample.time_s).toFixed(2)},${y(sample.value).toFixed(2)}`;
  }).join(" ");
  const seek = (time: number) => { if (canSeek && Number.isFinite(time) && time >= seekMin && time <= limit) onSeek(time); };
  const windowValid = verified && window && [window.start_s, window.end_s, window.critical_s].every(Number.isFinite) && window.end_s >= window.start_s;
  const windowStart = windowValid ? Math.max(minTime, window!.start_s) : 0;
  const windowEnd = windowValid ? Math.min(maxTime, window!.end_s) : 0;

  return <section className="telemetry-chart section-card min-w-0 p-5 sm:p-6">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold text-vf-navy">Telemetry</h2><span className="text-xs text-slate-500">{data.row_count} rows{data.downsampled ? " / sampled for display" : ""}</span></div>
    <nav aria-label="Telemetry signals" className="mt-3 flex flex-wrap gap-2">{signals.map((entry) => <button key={entry.key} type="button" aria-pressed={signal.key === entry.key} onClick={() => setSelected(entry.key)} className="telemetry-signal min-h-11 rounded-lg border border-slate-400/20 px-3 text-xs font-medium text-slate-600 transition hover:bg-teal-400/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-300">{entry.label}</button>)}</nav>
    <div className="mt-3 flex flex-wrap justify-between gap-2 text-xs"><span className="text-slate-600">{signal.label} / {signal.unit || "Unit unavailable"}</span><span className="text-slate-500">{verified ? currentSample ? `${format(currentSample.value!)} ${signal.unit || ""} at ${format(currentSample.time_s)}s` : "No sample at this video time" : "Video synchronization unavailable"}</span></div>
    <div className="mt-2 grid min-w-0 grid-cols-[3rem_minmax(0,1fr)] gap-1">
      <div aria-hidden="true" className="relative h-[180px] text-right text-[11px] tabular-nums text-slate-500">{[0, 0.5, 1].map((fraction) => <span key={fraction} className="absolute right-0 -translate-y-1/2" style={{ top: `${16 + fraction * 134}px` }}>{format(maxValue - fraction * (maxValue - minValue))}</span>)}</div>
      <div className="min-w-0">
    <svg viewBox="0 0 720 180" preserveAspectRatio="none" role="img" aria-label={`${signal.label} over ${data.time_basis === "video_seconds" ? "video" : "log"} seconds`} className="block h-[180px] w-full" onClick={(event) => {
      if (!canSeek) return;
      const bounds = event.currentTarget.getBoundingClientRect();
      if (!bounds.width) return;
      const plotX = (event.clientX - bounds.left) / bounds.width * 720;
      if (plotX < 55 || plotX > 704) return;
      seek(minTime + (plotX - 55) / 649 * timeSpan);
    }}>
      {[0, 0.5, 1].map((fraction) => <line key={fraction} x1="55" x2="704" y1={16 + fraction * 134} y2={16 + fraction * 134} stroke="currentColor" strokeOpacity="0.12" />)}
      {windowValid && windowEnd > windowStart && <rect x={x(windowStart)} y="16" width={x(windowEnd) - x(windowStart)} height="134" fill="#5eead4" fillOpacity="0.07" />}
      {windowValid && window!.critical_s >= minTime && window!.critical_s <= maxTime && <line x1={x(window!.critical_s)} x2={x(window!.critical_s)} y1="16" y2="150" stroke="#fde68a" strokeOpacity="0.5" strokeDasharray="3 4" />}
      <path d={path} fill="none" stroke="#5eead4" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      {samples.map((sample, index) => {
        const valid = (entry: typeof sample | undefined) => entry?.value !== null && entry?.value !== undefined && Number.isFinite(entry.value);
        return valid(sample) && !valid(samples[index - 1]) && !valid(samples[index + 1]) ? <circle key={index} cx={x(sample.time_s)} cy={y(sample.value!)} r="2.5" fill="#5eead4" /> : null;
      })}
      {cursorVisible && <line x1={x(currentTime)} x2={x(currentTime)} y1="16" y2="150" stroke="#cbd5e1" strokeWidth="1" />}
    </svg>
      <div aria-hidden="true" className="flex justify-between gap-1 pb-2 text-[11px] tabular-nums text-slate-500" style={{ paddingLeft: "7.64%", paddingRight: "2.22%" }}>{[0, 0.5, 1].map((fraction) => <span key={fraction}>{format(minTime + fraction * (maxTime - minTime))}s</span>)}</div>
      </div>
    </div>
    <label className="mt-1 block text-xs text-slate-500">{data.time_basis === "video_seconds" ? "Video seconds" : "Log seconds"}<input aria-label="Log timeline" type="range" disabled={!canSeek} min={seekMin} max={Math.max(seekMin, limit)} step="0.1" value={verified && seekEnabled && Number.isFinite(currentTime) ? Math.min(Math.max(currentTime, seekMin), Math.max(seekMin, limit)) : seekMin} onInput={(event) => seek(Number(event.currentTarget.value))} onChange={() => undefined} className="telemetry-timeline mt-1 h-11 w-full accent-teal-300 disabled:opacity-40" /></label>
    <p className="text-xs leading-5 text-slate-500">{canSeek ? "Click the chart or move the timeline to seek the video." : verified ? "Video seeking is currently unavailable." : "Log values are shown without a verified video alignment."}</p>
  </section>;
}

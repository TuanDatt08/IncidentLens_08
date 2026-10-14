"use client";

import { useEffect, useRef } from "react";

export type AnalysisProgressState = "idle" | "queued" | "running" | "succeeded" | "failed" | "cancelled";

export function AnalysisProgress({ value, state, paused = false, label = "Analysis progress" }: { value: number | null; state: AnalysisProgressState; paused?: boolean; label?: string }) {
  const displayed = useRef(0);
  const number = useRef<HTMLSpanElement>(null);
  const fill = useRef<HTMLDivElement>(null);
  const known = state === "succeeded" || state !== "idle" && state !== "queued" && value !== null && Number.isFinite(value);
  const percentage = state === "succeeded" ? 100 : known ? Math.min(99, Math.max(0, value!)) : 0;
  const active = !paused && (state === "queued" || state === "running");
  const text = known ? `${Math.round(percentage)}%` : state === "idle" ? "Not started" : state === "queued" ? "Queued" : state === "failed" ? "Failed" : state === "cancelled" ? "Cancelled" : "Working";
  useEffect(() => {
    let frame: number | undefined;
    let stopped = false;
    const preference = typeof window !== "undefined" && typeof window.matchMedia === "function" ? window.matchMedia("(prefers-reduced-motion: reduce)") : undefined;
    const paint = (next: number) => {
      displayed.current = next;
      if (number.current) number.current.textContent = known ? `${Math.round(next)}%` : text;
      if (fill.current) fill.current.style.transform = `scaleX(${next / 100})`;
    };
    const stop = () => { if (frame !== undefined) cancelAnimationFrame(frame); frame = undefined; };
    const snap = () => { stop(); paint(known ? percentage : 0); };
    const changed = () => { if (preference?.matches) snap(); };
    preference?.addEventListener("change", changed);
    if (!known || paused || state === "failed" || state === "cancelled" || preference?.matches) snap();
    else {
      const from = displayed.current;
      let started: number | undefined;
      paint(from);
      const tick = (timestamp: number) => {
        if (stopped) return;
        started ??= timestamp;
        const fraction = Math.min(1, Math.max(0, (timestamp - started) / 1800));
        const eased = 1 - Math.pow(1 - fraction, 3);
        paint(from + (percentage - from) * eased);
        if (fraction < 1) frame = requestAnimationFrame(tick);
        else frame = undefined;
      };
      frame = requestAnimationFrame(tick);
    }
    return () => { stopped = true; stop(); preference?.removeEventListener("change", changed); };
  }, [known, percentage, paused, state, text]);
  return <div className="analysis-progress" data-state={state} data-active={active} data-indeterminate={!known} data-zero={percentage === 0}>
    <div className="analysis-progress-caption flex items-center justify-between gap-3 text-sm"><span>{label}</span><span ref={number} aria-hidden="true" className="analysis-progress-value font-medium tabular-nums">{known ? "0%" : text}</span></div>
    <div className="analysis-progress-track relative mt-3 overflow-hidden rounded-full" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={known ? percentage : undefined} aria-valuetext={paused && active === false && (state === "queued" || state === "running") ? `${text}. Updates paused.` : text}>
      <div ref={fill} className="analysis-progress-fill absolute inset-0 origin-left" style={{ transform: "scaleX(0)" }}>{known && percentage > 0 && <div aria-hidden="true" className="analysis-progress-activity absolute inset-y-0" />}</div>
      {(!known || percentage === 0) && <div aria-hidden="true" className="analysis-progress-activity absolute inset-y-0" />}
    </div>
  </div>;
}

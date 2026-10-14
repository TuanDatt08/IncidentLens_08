"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { getIncidentTelemetry, getRecordingTelemetry } from "@/services/telemetry.service";
import type { TelemetryChart as TelemetryData } from "@/types/telemetry";
import { TelemetryChart } from "./telemetry-chart";

export function TelemetryPanel({ id, kind, currentTime, seekEnabled, onSeek, window, seekRange }: {
  id: string; kind: "incident" | "recording"; currentTime: number; seekEnabled: boolean;
  onSeek: (seconds: number) => void;
  window?: { start_s: number; critical_s: number; end_s: number } | null;
  seekRange?: { start_s: number; end_s: number };
}) {
  const [resource, setResource] = useState<{ id: string; kind: string; data?: TelemetryData; loading: boolean; error: string }>({ id, kind, loading: true, error: "" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setResource({ id, kind, loading: true, error: "" });
    const read = kind === "incident" ? getIncidentTelemetry : getRecordingTelemetry;
    void read(id, controller.signal).then(data => {
      if (!controller.signal.aborted) setResource({ id, kind, data, loading: false, error: "" });
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setResource({ id, kind, loading: false, error: cause instanceof Error ? cause.message : "Log signals could not be loaded." });
    });
    return () => controller.abort();
  }, [id, kind, attempt]);
  if (resource.id !== id || resource.kind !== kind || resource.loading) return <section className="section-card p-4" aria-label="Log signals" aria-busy="true"><p role="status" className="text-xs text-slate-500">Loading log signals…</p></section>;
  if (resource.error) return <section className="section-card space-y-3 p-4" aria-label="Log signals"><h2 className="text-sm font-semibold text-vf-navy">Log signals</h2><p role="alert" className="text-xs text-red-700">{resource.error}</p><Button variant="ghost" onClick={() => setAttempt(value => value + 1)}>Retry log signals</Button></section>;
  return resource.data ? <TelemetryChart data={resource.data} currentTime={currentTime} seekEnabled={seekEnabled} onSeek={onSeek} window={window} seekRange={seekRange} /> : null;
}

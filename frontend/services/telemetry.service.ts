import { apiRequest } from "@/lib/api-client";
import { AUTH_ENABLED, USE_MOCK_API } from "@/lib/config";
import { v2Request } from "./v2.service";
import type { TelemetryChart } from "@/types/telemetry";

export async function getIncidentTelemetry(id: string, signal?: AbortSignal): Promise<TelemetryChart> {
  if (!AUTH_ENABLED) return { state: "unavailable", time_basis: "log_seconds", alignment: "UNKNOWN", duration_s: null, row_count: 0, downsampled: false, signals: [], message: "Use the Qwen output and telemetry section for this deployment." };
  if (USE_MOCK_API) return { state: "unavailable", time_basis: "log_seconds", alignment: "UNKNOWN", duration_s: null, row_count: 0, downsampled: false, signals: [], message: "Telemetry is unavailable in mock mode." };
  // /telemetry serves the original CSV. Reuse the backend's aligned chart data.
  const context = await apiRequest<{
    time_basis: string; alignment: string; telemetry_error: string | null;
    points: { time_s: number; speed_kmh: number | null; brake_pct: number | null; acceleration: number | null }[];
  }>(`/incidents/${encodeURIComponent(id)}/review-context`, { signal });
  const available = context.alignment === "VERIFIED" && context.time_basis === "video_seconds" && !context.telemetry_error && context.points.length > 0;
  return {
    state: available ? "available" : "unavailable", time_basis: "video_seconds",
    alignment: context.alignment === "VERIFIED" ? "VERIFIED" : "UNKNOWN",
    // The response supplies chart points, not full-log duration or row counts.
    duration_s: null, row_count: context.points.length, downsampled: false,
    signals: available ? ([
      ["speed_kmh", "Speed", "km/h"], ["brake_pct", "Brake", "%"], ["acceleration", "Acceleration", "m/s²"],
    ] as const).map(([key, label, unit]) => ({ key, label, unit, samples: context.points.map(point => ({ time_s: point.time_s, value: point[key] })) })) : [],
    message: context.telemetry_error ?? (available ? null : "No verified telemetry samples are available."),
  };
}

export function getRecordingTelemetry(id: string, signal?: AbortSignal): Promise<TelemetryChart> {
  if (!AUTH_ENABLED) return Promise.resolve({ state: "unavailable", time_basis: "log_seconds", alignment: "UNKNOWN", duration_s: null, row_count: 0, downsampled: false, signals: [], message: "Telemetry charts are not enabled for this deployment." });
  return v2Request<TelemetryChart>(`/recordings/${encodeURIComponent(id)}/telemetry`, { signal });
}

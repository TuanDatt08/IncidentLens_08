import { apiRequest } from "@/lib/api-client";
import { AUTH_ENABLED, USE_MOCK_API } from "@/lib/config";
import { v2Request } from "./v2.service";
import type { TelemetryChart } from "@/types/telemetry";

export async function getIncidentTelemetry(id: string, signal?: AbortSignal): Promise<TelemetryChart> {
  if (!AUTH_ENABLED) return { state: "unavailable", time_basis: "log_seconds", alignment: "UNKNOWN", duration_s: null, row_count: 0, downsampled: false, signals: [], message: "Use the Qwen output and telemetry section for this deployment." };
  if (USE_MOCK_API) return { state: "unavailable", time_basis: "log_seconds", alignment: "UNKNOWN", duration_s: null, row_count: 0, downsampled: false, signals: [], message: "Telemetry is unavailable in mock mode." };
  return apiRequest<TelemetryChart>(`/incidents/${encodeURIComponent(id)}/telemetry`, { signal });
}

export function getRecordingTelemetry(id: string, signal?: AbortSignal): Promise<TelemetryChart> {
  if (!AUTH_ENABLED) return Promise.resolve({ state: "unavailable", time_basis: "log_seconds", alignment: "UNKNOWN", duration_s: null, row_count: 0, downsampled: false, signals: [], message: "Telemetry charts are not enabled for this deployment." });
  return v2Request<TelemetryChart>(`/recordings/${encodeURIComponent(id)}/telemetry`, { signal });
}

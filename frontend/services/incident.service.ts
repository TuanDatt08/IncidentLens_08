import { apiRequest, apiUpload, type UploadRequestOptions } from "@/lib/api-client";
import { API_BASE_URL, USE_MOCK_API } from "@/lib/config";
import type {
  IncidentRecord,
  IncidentListResponse,
  UploadIncidentInput,
  UploadIncidentResponse,
} from "@/types/incident";
import { mockStore } from "./mock-data";

export function getIncidentVideoUrl(incidentId: string): string | undefined {
  if (USE_MOCK_API) return mockStore.getVideoPreviewUrl(incidentId);
  return `${API_BASE_URL.replace(/\/+$/, "")}/incidents/${encodeURIComponent(incidentId)}/video`;
}

export async function getIncidentPreviewStatus(incidentId: string): Promise<{ state: "pending" | "ready" }> {
  if (USE_MOCK_API) return { state: "ready" };
  return { state: "ready" }; // Original Qwen media: no local preview worker required.
}

export async function listIncidents(limit = 20, offset = 0, signal?: AbortSignal): Promise<IncidentListResponse> {
  if (USE_MOCK_API) return mockStore.listIncidents(limit, offset);
  return apiRequest<IncidentListResponse>(`/incidents?limit=${limit}&offset=${offset}`, { signal });
}

export async function getIncident(incidentId: string): Promise<IncidentRecord> {
  if (USE_MOCK_API) {
    const incident = mockStore.getIncident(incidentId);
    if (!incident) throw new Error("Incident could not be found.");
    return incident;
  }
  return apiRequest<IncidentRecord>(`/incidents/${encodeURIComponent(incidentId)}`);
}

export async function uploadIncident(
  input: UploadIncidentInput,
  options: UploadRequestOptions = {},
): Promise<UploadIncidentResponse> {
  if (options.signal?.aborted) throw new DOMException("Upload cancelled.", "AbortError");
  if (USE_MOCK_API) return mockStore.addUpload(input);

  const formData = new FormData();
  formData.append("video", input.video);
  if (input.log) formData.append("log", input.log);
  if (input.syncOffset !== undefined) formData.append("sync_offset_s", String(input.syncOffset));
  if (input.syncMetadata) formData.append("sync_metadata", input.syncMetadata);
  return apiUpload<UploadIncidentResponse>("/incidents/upload", formData, options);
}

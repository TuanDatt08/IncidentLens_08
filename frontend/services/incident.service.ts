import { apiRequest, apiUpload, type UploadRequestOptions } from "@/lib/api-client";
import { API_BASE_URL, USE_MOCK_API } from "@/lib/config";
import type {
  IncidentRecord,
  IncidentListResponse,
  ProcessingStatus, ReviewState,
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

export async function listIncidents(limit = 20, offset = 0, signal?: AbortSignal, filters: { q?: string; processing_status?: ProcessingStatus; review_status?: ReviewState } = {}): Promise<IncidentListResponse> {
  if (USE_MOCK_API) {
    const all = mockStore.listIncidents(Number.MAX_SAFE_INTEGER, 0).items;
    const items = all.map(item => { const draft = item.processing_status === "COMPLETED" ? mockStore.getDraft(item.incident_id) : undefined; return { ...item, review_status: draft?.review_status ?? null, report_version: draft?.version ?? null }; });
    const summary: NonNullable<IncidentListResponse["summary"]> = { total: items.length, processing: {}, reviews: {} };
    for (const item of items) { summary.processing[item.processing_status] = (summary.processing[item.processing_status] ?? 0) + 1; if (item.review_status) summary.reviews[item.review_status] = (summary.reviews[item.review_status] ?? 0) + 1; }
    const q = filters.q?.trim().toLowerCase();
    const matches = items.filter(item => (!q || `${item.incident_id} ${item.incident_record?.scenario ?? ""}`.toLowerCase().includes(q)) && (!filters.processing_status || item.processing_status === filters.processing_status) && (!filters.review_status || item.review_status === filters.review_status));
    return { items: matches.slice(offset, offset + limit), total: matches.length, limit, offset, summary };
  }
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  return apiRequest<IncidentListResponse>(`/incidents?${params}`, { signal });
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

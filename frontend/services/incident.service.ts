import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import type {
  IncidentRecord,
  UploadIncidentInput,
  UploadIncidentResponse,
} from "@/types/incident";
import { mockStore } from "./mock-data";

export async function listIncidents(): Promise<IncidentRecord[]> {
  if (USE_MOCK_API) return mockStore.listIncidents();
  return apiRequest<IncidentRecord[]>("/incidents");
}

export async function getIncident(id: string): Promise<IncidentRecord> {
  if (USE_MOCK_API) {
    const incident = mockStore.getIncident(id);
    if (!incident) throw new Error("Incident could not be found.");
    return incident;
  }
  return apiRequest<IncidentRecord>(`/incidents/${encodeURIComponent(id)}`);
}

export async function uploadIncident(
  input: UploadIncidentInput,
): Promise<UploadIncidentResponse> {
  if (USE_MOCK_API) return mockStore.addUpload(input);

  const formData = new FormData();
  formData.append("video", input.video);
  if (input.log) formData.append("log", input.log);
  return apiRequest<UploadIncidentResponse>("/incidents/upload", {
    method: "POST",
    body: formData,
  });
}
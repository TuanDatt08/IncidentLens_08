import { apiRequest } from "@/lib/api-client";
import { API_BASE_URL, USE_MOCK_API } from "@/lib/config";
import type { Evidence, EvidenceListResponse } from "@/types/evidence";
import { mockStore } from "./mock-data";

export function getEvidenceMediaUrl(incidentId: string, evidenceId: string): string | undefined {
  if (USE_MOCK_API) return undefined;
  return `${API_BASE_URL.replace(/\/+$/, "")}/incidents/${encodeURIComponent(incidentId)}/evidence/${encodeURIComponent(evidenceId)}/media`;
}

export async function getEvidence(id: string): Promise<Evidence[]> {
  if (USE_MOCK_API) return mockStore.getEvidence(id);
  const response = await apiRequest<EvidenceListResponse>(`/incidents/${encodeURIComponent(id)}/evidence`);
  return response.items;
}

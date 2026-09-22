import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import type { Evidence } from "@/types/evidence";
import { mockStore } from "./mock-data";

export async function getEvidence(id: string): Promise<Evidence[]> {
  if (USE_MOCK_API) return mockStore.getEvidence(id);
  return apiRequest<Evidence[]>(`/incidents/${encodeURIComponent(id)}/evidence`);
}
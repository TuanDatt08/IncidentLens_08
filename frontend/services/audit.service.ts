import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import type { AuditEvent } from "@/types/audit";

export async function getIncidentAudit(id: string): Promise<AuditEvent[]> {
  if (USE_MOCK_API) {
    return [{
      event_id: `AUD-${id}`,
      incident_id: id,
      action: "report_loaded",
      actor: "system",
      role: "system",
      created_at: new Date().toISOString(),
      metadata: {},
    }];
  }
  return apiRequest<AuditEvent[]>(`/incidents/${encodeURIComponent(id)}/audit`);
}

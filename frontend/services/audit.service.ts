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
  const response = await apiRequest<{ incident_id: string; items: Omit<AuditEvent, "event_id" | "incident_id" | "role">[] }>(`/incidents/${encodeURIComponent(id)}/audit`);
  return response.items.map((event, index) => ({ ...event, event_id: `${id}:${index}:${event.created_at}`, incident_id: response.incident_id }));
}

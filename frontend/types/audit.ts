export type AuditEvent = {
  event_id: string;
  incident_id: string;
  action: string;
  actor: string | null;
  role?: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

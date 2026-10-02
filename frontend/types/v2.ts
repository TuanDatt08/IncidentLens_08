export type ClaimStatusV2 = "OBSERVED" | "SUPPORTED_INFERENCE" | "HYPOTHESIS" | "UNKNOWN";
export type ObservationV2 = { time_s: number; observation: string; evidence_ids: string[]; source: "VIDEO" | "TELEMETRY" | "FUSED"; certainty: ClaimStatusV2 };
export type FactorV2 = { category: "EXTERNAL_CONDITION" | "VEHICLE_OR_SYSTEM" | "HUMAN_INTERACTION" | "UNKNOWN"; label: string; claim_status: ClaimStatusV2; evidence_ids: string[] };
export type AnalysisV2 = {
  schema_version: "2.0"; incident_detected: boolean; time_basis: "video_seconds";
  event_type: "DISENGAGEMENT" | "HARD_BRAKING" | "COLLISION" | "CONTROL_ANOMALY" | "OTHER" | "UNKNOWN";
  window: { start_s: number; critical_s: number; end_s: number } | null;
  summary: string; timeline: ObservationV2[]; factors: FactorV2[]; unknowns: string[];
  review_status: "DRAFT" | "IN_REVIEW" | "APPROVED" | "REJECTED";
};
export type ReportV2 = { recording_id: string; candidate_id: string; report_id: string; version: number; analysis: AnalysisV2; provenance: Record<string, unknown>; submitted_by: string | null };
export type PageV2<T> = { items: T[]; next_cursor: string | null };
export type CandidateV2 = { candidate_id: string; recording_id: string; window: { start_s: number; critical_s: number; end_s: number }; reasons: string[]; analysis_state: "PENDING" | "UNANALYZED" | "ANALYZED" | "NO_DETECTION"; report_id: string | null };
export type JobV2 = { job_id: string; recording_id: string; status: "queued" | "running" | "succeeded" | "failed" | "cancelled"; stage: string; attempt: number; progress: { done: number; total: number | null }; coverage: { unknowns?: string[]; sampled_frames?: number; log_rows?: number }; budget: { calls_used: number; max_calls: number }; partial_results: { report_id?: string; candidate_id?: string }[]; error: { code: string; message: string } | null };
export type EvidenceV2 = { evidence_id: string; source: string; start_s: number; end_s: number; media_type: string; privacy_state: string; privacy_validation: string; media_url: string | null };
export type AuditV2 = { version: number; actor: string; action: string; reason: string | null; created_at: string };
export type SessionV2 = { subject: string; roles: ("Engineer" | "Reviewer")[] };
export type UploadV2 = { upload_id: string; recording_id: string; part_size: number; part_count: number; parts: { number: number; bytes: number; sha256: string }[]; status: string; expires_at: string };

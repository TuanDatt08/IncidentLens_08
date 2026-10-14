export type ProcessingStatus =
  | "UPLOADED"
  | "READY"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export type ReviewState = "DRAFT" | "IN_REVIEW" | "APPROVED" | "REJECTED";

export type IncidentDraft = {
  incident_id: string;
  incident_detected: boolean;
  incident_type: string | null;
  incident_window: { start: number; critical: number; end: number } | null;
  summary: string | null;
  timeline: unknown[];
  observations: unknown[];
  key_factors: unknown[];
  unknowns: unknown[];
  evidence_ids: string[];
  review_status: ReviewState;
  version: number;
  created_at: string | null;
  updated_at: string | null;
  rejection_reason?: string;
};

export type AnalysisCoverage = {
  state: "available" | "unknown";
  time_basis: "video_seconds";
  duration_s: number | null;
  sampled_timestamps_s: number[];
  sampled_frame_count: number | null;
  telemetry_alignment: string;
  limitations: string[];
};

export type IncidentRecord = {
  incident_id: string;
  processing_status: ProcessingStatus;
  video_uri: string;
  telemetry_uri: string | null;
  video_metadata: VideoMetadata | null;
  telemetry_metadata: Record<string, unknown> | null;
  incident_record: {
    scenario?: string | null;
    template?: "rear_end" | "pedestrian" | null;
    [key: string]: unknown;
  } | null;
  created_at: string;
  updated_at: string;
};

export type IncidentListResponse = {
  items: IncidentRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type VideoMetadata = {
  duration: number;
  fps: number;
  width: number;
  height: number;
  collision_offset_in_video_s?: number | null;
};

export type UploadIncidentResponse = {
  incident_id: string;
  processing_status: "READY";
  sync_offset: number | null;
  frame_count: number;
  video_metadata: VideoMetadata;
};

export type UploadIncidentInput = {
  video: File;
  log?: File;
    syncOffset?: number;
    syncMetadata?: File;
};

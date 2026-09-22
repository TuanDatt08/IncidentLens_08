export type ProcessingStatus =
  | "UPLOADED"
  | "VALIDATING"
  | "EXTRACTING"
  | "SYNCHRONIZING"
  | "PROCESSING"
  | "PASS_1"
  | "PASS_2"
  | "COMPLETED"
  | "FAILED";

export type ReviewState = "DRAFT" | "IN_REVIEW" | "APPROVED" | "REJECTED";

// NEED_CONFIRMATION: timeline shape is provisional until the backend schema is frozen.
export type TimelineItem = {
  label: string;
  timestamp_sec: number;
  description?: string;
};

export type IncidentDraft = {
  id: string;
  package_id: string;
  incident_type: string;
  confidence: number;
  start_sec: number;
  critical_sec: number;
  end_sec: number;
  summary_text: string;
  unknowns: string[];
  status: ReviewState;
  created_at: string;

  // NEED_CONFIRMATION: these report fields are intentionally optional for MVP.
  timeline?: TimelineItem[];
  observations?: string[];
  key_factors?: string[];
  evidence_ids?: string[];
  rejection_reason?: string;
};

export type IncidentRecord = {
  id: string;
  package_id: string;
  file_name: string;
  created_at: string;
  processing_status: ProcessingStatus;
  report_status: ReviewState;
  video_url?: string;
  progress?: number;
  frame_count?: number;
};

export type UploadIncidentResponse = {
  package_id: string;
  status: string;
  sync_offset: number | null;
  frame_count: number;
  video_metadata?: {
    duration: number;
    fps: number;
    width: number;
    height: number;
  } | null;
  warnings: string[];
};

export type UploadIncidentInput = {
  video: File;
  log?: File;
};
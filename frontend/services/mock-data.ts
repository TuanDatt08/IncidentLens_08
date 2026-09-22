import type { Evidence } from "@/types/evidence";
import type {
  IncidentDraft,
  IncidentRecord,
  ProcessingStatus,
  ReviewState,
  UploadIncidentInput,
  UploadIncidentResponse,
} from "@/types/incident";
import type { ProgressEvent } from "@/types/processing";
import type { ReportPatch } from "@/types/report";

const sampleVideo =
  "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4";

const initialIncidents: IncidentRecord[] = [
  {
    id: "RAV-18-0042",
    package_id: "RAV-18-0042",
    file_name: "rav18_city_merge_0042.mp4",
    created_at: "2026-09-21T09:42:00.000Z",
    processing_status: "COMPLETED",
    report_status: "DRAFT",
    video_url: sampleVideo,
    progress: 100,
    frame_count: 901,
  },
  {
    id: "RAV-18-0041",
    package_id: "RAV-18-0041",
    file_name: "highway_cut_in_0041.mp4",
    created_at: "2026-09-20T15:08:00.000Z",
    processing_status: "PROCESSING",
    report_status: "DRAFT",
    video_url: sampleVideo,
    progress: 50,
    frame_count: 1240,
  },
  {
    id: "RAV-18-0039",
    package_id: "RAV-18-0039",
    file_name: "urban_crossing_0039.mp4",
    created_at: "2026-09-19T11:24:00.000Z",
    processing_status: "COMPLETED",
    report_status: "APPROVED",
    video_url: sampleVideo,
    progress: 100,
    frame_count: 1384,
  },
  {
    id: "RAV-18-0038",
    package_id: "RAV-18-0038",
    file_name: "night_drive_0038.mp4",
    created_at: "2026-09-18T18:16:00.000Z",
    processing_status: "FAILED",
    report_status: "DRAFT",
    progress: 34,
    frame_count: 0,
  },
];

const incidents = [...initialIncidents];

const draftStore: Record<string, IncidentDraft> = {
  "RAV-18-0042": {
    id: "RAV-18-0042",
    package_id: "RAV-18-0042",
    incident_type: "Hard Braking",
    confidence: 0.89,
    start_sec: 11.5,
    critical_sec: 14.2,
    end_sec: 17,
    summary_text:
      "The ego vehicle performs a hard braking manoeuvre after a lead vehicle enters the lane and slows rapidly.",
    unknowns: ["Brake pedal intent is not available in the current telemetry package."],
    status: "DRAFT",
    created_at: "2026-09-21T09:42:00.000Z",
    timeline: [
      { label: "Start", timestamp_sec: 11.5, description: "Lead vehicle enters the incident window." },
      { label: "Critical", timestamp_sec: 14.2, description: "Peak deceleration is observed." },
      { label: "End", timestamp_sec: 17, description: "Vehicle returns to stable motion." },
    ],
    observations: ["Lead vehicle brake lights become visible."],
    key_factors: ["Short following distance", "Rapid lead-vehicle deceleration"],
    evidence_ids: ["EV-001", "EV-002"],
  },
  "RAV-18-0039": {
    id: "RAV-18-0039",
    package_id: "RAV-18-0039",
    incident_type: "Pedestrian Crossing",
    confidence: 0.94,
    start_sec: 6.8,
    critical_sec: 9.1,
    end_sec: 12.4,
    summary_text: "The perception stack detects a pedestrian crossing ahead and the vehicle yields safely.",
    unknowns: [],
    status: "APPROVED",
    created_at: "2026-09-19T11:24:00.000Z",
    timeline: [
      { label: "Start", timestamp_sec: 6.8 },
      { label: "Critical", timestamp_sec: 9.1 },
      { label: "End", timestamp_sec: 12.4 },
    ],
    observations: ["Pedestrian is visible near the right-side crossing."],
    key_factors: ["Clear lane boundary", "Vehicle yields before crossing"],
    evidence_ids: ["EV-014"],
  },
};

const evidenceStore: Record<string, Evidence[]> = {
  "RAV-18-0042": [
    {
      evidence_id: "EV-001",
      timestamp_sec: 13.8,
      source: "VIDEO",
      description: "Lead vehicle brake lights become visible.",
    },
    {
      evidence_id: "EV-002",
      timestamp_sec: 14.2,
      source: "VIDEO",
      description: "Ego vehicle reaches the critical braking moment.",
    },
  ],
  "RAV-18-0039": [
    {
      evidence_id: "EV-014",
      timestamp_sec: 9.1,
      source: "VIDEO",
      description: "Pedestrian enters the vehicle path and is tracked continuously.",
    },
  ],
};

function createFallbackDraft(incident: IncidentRecord): IncidentDraft {
  return {
    id: incident.id,
    package_id: incident.package_id,
    incident_type: "Incident under analysis",
    confidence: 0,
    start_sec: 0,
    critical_sec: 0,
    end_sec: 0,
    summary_text: "The AI-generated incident summary will appear here after analysis.",
    unknowns: ["Analysis has not produced additional unknowns yet."],
    status: incident.report_status,
    created_at: incident.created_at,
    observations: [],
    key_factors: [],
    timeline: [],
    evidence_ids: [],
  };
}

export const mockStore = {
  listIncidents(): IncidentRecord[] {
    return incidents.map((incident) => ({ ...incident }));
  },

  getIncident(id: string): IncidentRecord | undefined {
    const incident = incidents.find((item) => item.id === id);
    return incident ? { ...incident } : undefined;
  },

  getDraft(id: string): IncidentDraft | undefined {
    const incident = incidents.find((item) => item.id === id);
    if (!incident) return undefined;
    const draft = draftStore[id] ?? createFallbackDraft(incident);
    return {
      ...draft,
      unknowns: [...draft.unknowns],
      observations: [...(draft.observations ?? [])],
      key_factors: [...(draft.key_factors ?? [])],
      timeline: [...(draft.timeline ?? [])],
    };
  },

  getEvidence(id: string): Evidence[] {
    return (evidenceStore[id] ?? []).map((item) => ({ ...item }));
  },

  updateReport(id: string, patch: ReportPatch): IncidentDraft {
    const current = this.getDraft(id);
    if (!current) throw new Error("Incident report was not found.");
    const next = { ...current, ...patch };
    draftStore[id] = next;
    const incident = incidents.find((item) => item.id === id);
    if (incident) incident.report_status = next.status;
    return this.getDraft(id) as IncidentDraft;
  },

  setReportStatus(id: string, status: ReviewState, rejectionReason?: string): IncidentDraft {
    const current = this.getDraft(id);
    if (!current) throw new Error("Incident report was not found.");
    const next = {
      ...current,
      ...(rejectionReason !== undefined ? { rejection_reason: rejectionReason } : {}),
    };
    next.status = status;
    draftStore[id] = next;
    const incident = incidents.find((item) => item.id === id);
    if (incident) incident.report_status = status;
    return this.getDraft(id) as IncidentDraft;
  },

  addUpload(input: UploadIncidentInput): UploadIncidentResponse {
    const numericIds = incidents
      .map((incident) => Number(incident.id.split("-").at(-1)))
      .filter((value) => Number.isFinite(value));
    const nextNumber = Math.max(...numericIds, 0) + 1;
    const id = `RAV-18-${String(nextNumber).padStart(4, "0")}`;
    const now = new Date().toISOString();
    const videoUrl = URL.createObjectURL(input.video);
    incidents.unshift({
      id,
      package_id: id,
      file_name: input.video.name,
      created_at: now,
      processing_status: "UPLOADED",
      report_status: "DRAFT",
      video_url: videoUrl,
      progress: 0,
      frame_count: 0,
    });
    draftStore[id] = {
      ...createFallbackDraft(incidents[0]),
      id,
      package_id: id,
      created_at: now,
      status: "DRAFT",
    };
    evidenceStore[id] = [];
    return {
      package_id: id,
      status: "UPLOADED",
      sync_offset: null,
      frame_count: 0,
      video_metadata: null,
      warnings: [],
    };
  },

  setProcessing(id: string, status: ProcessingStatus, progress: number): void {
    const incident = incidents.find((item) => item.id === id);
    if (incident) {
      incident.processing_status = status;
      incident.progress = progress;
    }
  },
};

export const mockProgressEvents: ProgressEvent[] = [
  { progress: 0, stage: "UPLOADED", message: "Package received and queued for analysis." },
  { progress: 12, stage: "VALIDATING", message: "Checking video and telemetry package." },
  { progress: 27, stage: "EXTRACTING", message: "Extracting frames and vehicle signals." },
  { progress: 39, stage: "SYNCHRONIZING", message: "Synchronizing video with the available log." },
  { progress: 50, stage: "PASS_1", message: "Pass 1 — Incident window located." },
  { progress: 78, stage: "PASS_2", message: "Pass 2 — Incident and evidence analysis in progress." },
  { progress: 100, stage: "COMPLETED", message: "Analysis complete. Draft report is ready to review." },
];
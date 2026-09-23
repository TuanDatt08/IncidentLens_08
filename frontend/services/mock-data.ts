import type { Evidence } from "@/types/evidence";
import type {
  IncidentDraft,
  IncidentListResponse,
  IncidentRecord,
  ProcessingStatus,
  ReviewState,
  UploadIncidentInput,
  UploadIncidentResponse,
  VideoMetadata,
} from "@/types/incident";
import type { ReportPatch } from "@/types/report";

const sampleVideo =
  "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4";

const initialIncidents: IncidentRecord[] = [
  {
    incident_id: "RAV-18-0042",
    created_at: "2026-09-21T09:42:00.000Z",
    updated_at: "2026-09-21T09:42:00.000Z",
    processing_status: "COMPLETED",
    video_uri: "RAV-18-0042/source/video.mp4",
    telemetry_uri: null,
    video_metadata: { duration: 5, fps: 30, width: 1920, height: 1080, collision_offset_in_video_s: 2.5 },
    telemetry_metadata: null,
    incident_record: { scenario: "city_merge", template: "rear_end" },
  },
  {
    incident_id: "RAV-18-0041",
    created_at: "2026-09-20T15:08:00.000Z",
    updated_at: "2026-09-20T15:08:00.000Z",
    processing_status: "PROCESSING",
    video_uri: "RAV-18-0041/source/video.mp4",
    telemetry_uri: null,
    video_metadata: { duration: 40, fps: 30, width: 1920, height: 1080 },
    telemetry_metadata: null,
    incident_record: { scenario: "highway_cut_in", template: "rear_end" },
  },
  {
    incident_id: "RAV-18-0039",
    created_at: "2026-09-19T11:24:00.000Z",
    updated_at: "2026-09-19T11:24:00.000Z",
    processing_status: "COMPLETED",
    video_uri: "RAV-18-0039/source/video.mp4",
    telemetry_uri: null,
    video_metadata: { duration: 5, fps: 30, width: 1920, height: 1080, collision_offset_in_video_s: 2.5 },
    telemetry_metadata: null,
    incident_record: { scenario: "urban_crossing", template: "pedestrian" },
  },
  {
    incident_id: "RAV-18-0038",
    created_at: "2026-09-18T18:16:00.000Z",
    updated_at: "2026-09-18T18:16:00.000Z",
    processing_status: "FAILED",
    video_uri: "RAV-18-0038/source/video.mp4",
    telemetry_uri: null,
    video_metadata: { duration: 25, fps: 30, width: 1920, height: 1080 },
    telemetry_metadata: null,
    incident_record: null,
  },
];

const incidents = [...initialIncidents];
const mockVideoUrls = new Map(initialIncidents.map((incident) => [incident.incident_id, sampleVideo]));

const draftStore: Record<string, IncidentDraft> = {
  "RAV-18-0042": {
    incident_id: "RAV-18-0042",
    incident_detected: true,
    incident_type: "Hard Braking",
    incident_window: { start: -1, critical: 0, end: 1 },
    summary:
      "The ego vehicle performs a hard braking manoeuvre after a lead vehicle enters the lane and slows rapidly.",
    unknowns: ["Brake pedal intent is not available in the current telemetry package."],
    review_status: "DRAFT",
    version: 1,
    created_at: "2026-09-21T09:42:00.000Z",
    updated_at: "2026-09-21T09:42:00.000Z",
    timeline: [
      { label: "Start", timestamp_sec: -1, description: "Lead vehicle enters the incident window." },
      { label: "Critical", timestamp_sec: 0, description: "Peak deceleration is observed." },
      { label: "End", timestamp_sec: 1, description: "Vehicle returns to stable motion." },
    ],
    observations: ["Lead vehicle brake lights become visible."],
    key_factors: ["Short following distance", "Rapid lead-vehicle deceleration"],
    evidence_ids: ["EV-001", "EV-002"],
  },
  "RAV-18-0039": {
    incident_id: "RAV-18-0039",
    incident_detected: true,
    incident_type: "Pedestrian Crossing",
    incident_window: { start: -1, critical: 0, end: 1 },
    summary: "The perception stack detects a pedestrian crossing ahead and the vehicle yields safely.",
    unknowns: [],
    review_status: "APPROVED",
    version: 1,
    created_at: "2026-09-19T11:24:00.000Z",
    updated_at: "2026-09-19T11:24:00.000Z",
    timeline: [
      { label: "Start", timestamp_sec: -1 },
      { label: "Critical", timestamp_sec: 0 },
      { label: "End", timestamp_sec: 1 },
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
      kind: "video",
      uri: "RAV-18-0042/evidence/lead-brake-lights.mp4",
      sha256: "a".repeat(64),
      time_range_s: [-0.4, -0.2],
      tier: "core",
      bytes: 245760,
      media_type: "video/mp4",
    },
    {
      evidence_id: "EV-002",
      kind: "frame",
      uri: "RAV-18-0042/evidence/critical-frame.jpg",
      sha256: "b".repeat(64),
      time_range_s: [0, 0],
      tier: "core",
      bytes: 53248,
      media_type: "image/jpeg",
    },
  ],
  "RAV-18-0039": [
    {
      evidence_id: "EV-014",
      kind: "video",
      uri: "RAV-18-0039/evidence/pedestrian-crossing.mp4",
      sha256: "c".repeat(64),
      time_range_s: [-0.1, 0.1],
      tier: "bulky",
      bytes: 327680,
      media_type: "video/mp4",
    },
  ],
};

function createFallbackDraft(incident: IncidentRecord): IncidentDraft {
  return {
    incident_id: incident.incident_id,
    incident_detected: false,
    incident_type: null,
    incident_window: null,
    summary: "The AI-generated incident summary will appear here after analysis.",
    unknowns: ["Analysis has not produced additional unknowns yet."],
    review_status: "DRAFT",
    version: 1,
    created_at: incident.created_at,
    updated_at: incident.updated_at,
    observations: [],
    key_factors: [],
    timeline: [],
    evidence_ids: [],
  };
}

export const mockStore = {
  listIncidents(limit = 20, offset = 0): IncidentListResponse {
    return { items: incidents.slice(offset, offset + limit).map((incident) => ({ ...incident })), total: incidents.length, limit, offset };
  },

  getIncident(id: string): IncidentRecord | undefined {
    const incident = incidents.find((item) => item.incident_id === id);
    return incident ? { ...incident } : undefined;
  },

  getVideoPreviewUrl(id: string): string | undefined {
    return mockVideoUrls.get(id);
  },

  getDraft(id: string): IncidentDraft | undefined {
    const incident = incidents.find((item) => item.incident_id === id);
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
    return (evidenceStore[id] ?? []).map((item) => ({ ...item, time_range_s: [...item.time_range_s] as [number, number] }));
  },

  updateReport(id: string, patch: ReportPatch): IncidentDraft {
    const current = this.getDraft(id);
    if (!current) throw new Error("Incident report was not found.");
    const { version: _version, ...fields } = patch;
    const next = { ...current, ...fields, version: current.version + 1, updated_at: new Date().toISOString() };
    draftStore[id] = next;
    return this.getDraft(id) as IncidentDraft;
  },

  setReportStatus(id: string, status: ReviewState, rejectionReason?: string): IncidentDraft {
    const current = this.getDraft(id);
    if (!current) throw new Error("Incident report was not found.");
    const next = {
      ...current,
      ...(rejectionReason !== undefined ? { rejection_reason: rejectionReason } : {}),
    };
    next.review_status = status;
    next.updated_at = new Date().toISOString();
    draftStore[id] = next;
    return this.getDraft(id) as IncidentDraft;
  },

  addUpload(input: UploadIncidentInput): UploadIncidentResponse {
    const numericIds = incidents
      .map((incident) => Number(incident.incident_id.split("-").at(-1)))
      .filter((value) => Number.isFinite(value));
    const nextNumber = Math.max(...numericIds, 0) + 1;
    const id = `RAV-18-${String(nextNumber).padStart(4, "0")}`;
    const now = new Date().toISOString();
    const videoUri = `${id}/source/video.mp4`;
    mockVideoUrls.set(id, URL.createObjectURL(input.video));
    const videoMetadata: VideoMetadata = { duration: 0, fps: 0, width: 0, height: 0 };
    incidents.unshift({
      incident_id: id,
      created_at: now,
      updated_at: now,
      processing_status: "READY",
      video_uri: videoUri,
      telemetry_uri: null,
      video_metadata: videoMetadata,
      telemetry_metadata: null,
      incident_record: null,
    });
    draftStore[id] = {
      ...createFallbackDraft(incidents[0]),
      incident_id: id,
      created_at: now,
      review_status: "DRAFT",
    };
    evidenceStore[id] = [];
    return {
      incident_id: id,
      processing_status: "READY",
      sync_offset: null,
      frame_count: 0,
      video_metadata: videoMetadata,
    };
  },

  setProcessing(id: string, status: ProcessingStatus): void {
    const incident = incidents.find((item) => item.incident_id === id);
    if (incident) {
      incident.processing_status = status;
      incident.updated_at = new Date().toISOString();
    }
  },
};

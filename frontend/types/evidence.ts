export type Evidence = {
  evidence_id: string;
  kind: "video" | "telemetry" | "frame" | "annotation";
  uri: string;
  sha256: string;
  time_range_s: [number, number];
  tier: "core" | "bulky" | null;
  bytes: number | null;
  media_type: string | null;
};

export type EvidenceListResponse = {
  incident_id: string;
  items: Evidence[];
};

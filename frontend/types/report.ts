import type { ReviewState } from "./incident";

export type EditableReportFields = {
  summary: string | null;
  observations: unknown[];
  key_factors: unknown[];
  unknowns: unknown[];
  timeline: unknown[];
};

export type ReportPatch = { version: number } & Partial<EditableReportFields>;

export type ReportActionResponse = {
  incident_id: string;
  status: ReviewState;
  version: number;
  rejection_reason: string | null;
};

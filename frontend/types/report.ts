import type { IncidentDraft, ReviewState, TimelineItem } from "./incident";

// NEED_CONFIRMATION: report fields are kept separate from the AI draft so PATCH
// requests can send only fields that an engineer actually changed.
export type EditableReportFields = {
  summary_text: string;
  observations: string[];
  key_factors: string[];
  unknowns: string[];
  timeline?: TimelineItem[];
};

export type ReportPatch = Partial<EditableReportFields>;

export type ReportActionResponse = {
  status: ReviewState;
  report?: IncidentDraft;
  rejection_reason?: string;
};

export type ReportData = IncidentDraft & EditableReportFields;
import { ApiError } from "@/lib/api-client";
import { getIncidentReport } from "./report.service";
import type { IncidentRecord, ReviewState } from "@/types/incident";

export type IncidentReviewSummary =
  | { state: "available"; status: ReviewState; version: number }
  | { state: "missing" | "error" };

// The list API exposes processing only. Read actual report state, never infer approval.
export async function loadIncidentReviews(
  incidents: IncidentRecord[], signal: AbortSignal,
  onResult: (id: string, summary: IncidentReviewSummary) => void,
): Promise<void> {
  const completed = incidents.filter((item) => item.processing_status === "COMPLETED");
  let next = 0;
  let stopped = false;
  async function worker() {
    while (!signal.aborted && !stopped && next < completed.length) {
      const incident = completed[next++];
      let summary: IncidentReviewSummary;
      try {
        const report = await getIncidentReport(incident.incident_id, signal);
        if (!["DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"].includes(report.review_status)) throw new Error("Unknown review state");
        summary = { state: "available", status: report.review_status, version: report.version };
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) stopped = true;
        summary = { state: error instanceof ApiError && error.status === 404 ? "missing" : "error" };
      }
      if (!signal.aborted) onResult(incident.incident_id, summary);
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, completed.length) }, worker));
}

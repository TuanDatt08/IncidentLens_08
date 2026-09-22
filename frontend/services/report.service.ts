import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import type { IncidentDraft, ReviewState } from "@/types/incident";
import type { ReportActionResponse, ReportPatch } from "@/types/report";
import { mockStore } from "./mock-data";

export async function getIncidentReport(id: string): Promise<IncidentDraft> {
  if (USE_MOCK_API) {
    const report = mockStore.getDraft(id);
    if (!report) throw new Error("Incident report could not be found.");
    return report;
  }
  return apiRequest<IncidentDraft>(`/incidents/${encodeURIComponent(id)}/report`);
}

export async function updateReport(id: string, patch: ReportPatch): Promise<IncidentDraft> {
  if (USE_MOCK_API) return mockStore.updateReport(id, patch);
  return apiRequest<IncidentDraft>(`/incidents/${encodeURIComponent(id)}/report`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function submitReport(id: string): Promise<ReportActionResponse> {
  if (USE_MOCK_API) {
    return { status: mockStore.setReportStatus(id, "IN_REVIEW").status };
  }
  return apiRequest<ReportActionResponse>(`/incidents/${encodeURIComponent(id)}/report/submit`, {
    method: "POST",
  });
}

export async function approveReport(id: string): Promise<ReportActionResponse> {
  if (USE_MOCK_API) {
    return { status: mockStore.setReportStatus(id, "APPROVED").status };
  }
  return apiRequest<ReportActionResponse>(`/incidents/${encodeURIComponent(id)}/report/approve`, {
    method: "POST",
  });
}

export async function rejectReport(id: string, reason: string): Promise<ReportActionResponse> {
  if (USE_MOCK_API) {
    return {
      status: mockStore.setReportStatus(id, "REJECTED", reason).status,
      rejection_reason: reason,
    };
  }
  return apiRequest<ReportActionResponse>(`/incidents/${encodeURIComponent(id)}/report/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function isEditableReviewState(status: ReviewState): boolean {
  return status === "DRAFT" || status === "REJECTED";
}
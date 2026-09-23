import { ApiError, apiRequest, parseApiError } from "@/lib/api-client";
import { API_BASE_URL, USE_MOCK_API } from "@/lib/config";
import type { IncidentDraft, ReviewState } from "@/types/incident";
import type { ReportActionResponse, ReportPatch } from "@/types/report";
import { mockStore } from "./mock-data";

export class ReportConflictError extends ApiError {
  constructor(message: string, readonly currentVersion?: number, code?: string, details?: unknown) {
    super(message, 409, code, details);
    this.name = "ReportConflictError";
  }
}

export async function getIncidentReport(id: string): Promise<IncidentDraft> {
  if (USE_MOCK_API) {
    const report = mockStore.getDraft(id);
    if (!report) throw new Error("Incident report could not be found.");
    return report;
  }
  return apiRequest<IncidentDraft>(`/incidents/${encodeURIComponent(id)}/report`);
}

export async function updateReport(id: string, patch: ReportPatch): Promise<IncidentDraft> {
  if (USE_MOCK_API) {
    const current = mockStore.getDraft(id);
    if (current && patch.version !== current.version) throw new ReportConflictError("Report version is stale.", current.version);
    return mockStore.updateReport(id, patch);
  }
  const response = await fetch(`${API_BASE_URL}/incidents/${encodeURIComponent(id)}/report`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!response.ok) {
    const error = await parseApiError(response);
    if (response.status === 409) {
      const details = error.details;
      const currentVersion = details && typeof details === "object" && "current_version" in details && typeof details.current_version === "number"
        ? details.current_version
        : undefined;
      throw new ReportConflictError(error.message, currentVersion, error.code, error.details);
    }
    throw error;
  }
  return response.json() as Promise<IncidentDraft>;
}

export async function submitReport(id: string): Promise<ReportActionResponse> {
  if (USE_MOCK_API) {
    const report = mockStore.setReportStatus(id, "IN_REVIEW");
    return { incident_id: id, status: report.review_status, version: report.version, rejection_reason: null };
  }
  return apiRequest<ReportActionResponse>(`/incidents/${encodeURIComponent(id)}/report/submit`, {
    method: "POST",
  });
}

export async function approveReport(id: string): Promise<ReportActionResponse> {
  if (USE_MOCK_API) {
    const report = mockStore.setReportStatus(id, "APPROVED");
    return { incident_id: id, status: report.review_status, version: report.version, rejection_reason: null };
  }
  return apiRequest<ReportActionResponse>(`/incidents/${encodeURIComponent(id)}/report/approve`, {
    method: "POST",
  });
}

export async function rejectReport(id: string, reason: string): Promise<ReportActionResponse> {
  if (USE_MOCK_API) {
    const report = mockStore.setReportStatus(id, "REJECTED", reason);
    return {
      incident_id: id,
      status: report.review_status,
      version: report.version,
      rejection_reason: reason,
    };
  }
  return apiRequest<ReportActionResponse>(`/incidents/${encodeURIComponent(id)}/report/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function isEditableReviewState(status: ReviewState): boolean {
  return status === "DRAFT";
}

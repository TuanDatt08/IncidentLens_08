import { apiRequest } from "@/lib/api-client";
import { USE_MOCK_API } from "@/lib/config";
import type { AnalysisJob, AnalyzeAccepted } from "@/types/processing";
import { mockStore } from "./mock-data";

const mockJobs = new Map<string, { incidentId: string; step: number }>();
const pendingAnalysis = new Map<string, Promise<AnalyzeAccepted>>();
const jobStorageKey = (id: string) => `analysis-job:${id}`;

export function getStoredJobId(id: string): string | null {
  return USE_MOCK_API ? null : window.sessionStorage.getItem(jobStorageKey(id));
}

export function clearStoredJobId(id: string): void {
  if (!USE_MOCK_API) window.sessionStorage.removeItem(jobStorageKey(id));
}

export async function analyzeIncident(id: string): Promise<AnalyzeAccepted> {
  const pending = pendingAnalysis.get(id);
  if (pending) return pending;
  if (USE_MOCK_API) {
    const job_id = `MOCK-${id}-${Date.now()}`;
    mockJobs.set(job_id, { incidentId: id, step: 0 });
    mockStore.setProcessing(id, "PROCESSING");
    return { job_id, incident_id: id, status: "queued" };
  }
  const request = apiRequest<AnalyzeAccepted>(`/incidents/${encodeURIComponent(id)}/analyze`, {
    method: "POST",
  }).then((accepted) => {
    window.sessionStorage.setItem(jobStorageKey(id), accepted.job_id);
    return accepted;
  }).finally(() => pendingAnalysis.delete(id));
  pendingAnalysis.set(id, request);
  return request;
}

export async function getAnalysisJob(jobId: string): Promise<AnalysisJob> {
  if (USE_MOCK_API) {
    const mock = mockJobs.get(jobId);
    if (!mock) throw new Error("Analysis job could not be found.");
    const snapshots: Pick<AnalysisJob, "status" | "pass" | "progress">[] = [
      { status: "queued", pass: null, progress: { done: 0, total: null } },
      { status: "running", pass: 1, progress: { done: 2, total: 10 } },
      { status: "running", pass: 1, progress: { done: 10, total: 10 } },
      { status: "running", pass: 2, progress: { done: 4, total: 10 } },
      { status: "succeeded", pass: 2, progress: { done: 10, total: 10 } },
    ];
    const snapshot = snapshots[Math.min(mock.step, snapshots.length - 1)];
    mock.step += 1;
    if (snapshot.status === "succeeded") mockStore.setProcessing(mock.incidentId, "COMPLETED");
    return { job_id: jobId, ...snapshot, updated_at: new Date().toISOString(), result_uri: null, error: null };
  }
  return apiRequest<AnalysisJob>(`/jobs/${encodeURIComponent(jobId)}`);
}

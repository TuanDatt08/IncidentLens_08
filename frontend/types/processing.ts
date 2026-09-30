export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export type AnalyzeAccepted = {
  job_id: string;
  incident_id: string;
  status: "queued";
};

export type AnalysisJob = {
  job_id: string;
  status: JobStatus;
  pass: 1 | 2 | null;
  progress: { done: number; total: number | null };
  updated_at: string;
  result_uri: string | null;
  error: { code?: string; message?: string } | null;
};

export type ProcessingStage = "QUEUED" | "RUNNING" | "PASS_1" | "PASS_2" | "COMPLETED" | "FAILED" | "CANCELLED";

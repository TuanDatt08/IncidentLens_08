import type { ProcessingStatus } from "./incident";

export type ProgressEvent = {
  progress: number;
  stage: ProcessingStatus | string;
  message?: string;
};

export type ProcessingStage = {
  key: ProcessingStatus;
  label: string;
  description: string;
};
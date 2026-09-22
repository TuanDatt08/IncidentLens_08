import type { ProcessingStatus, ReviewState } from "@/types/incident";

type BadgeStatus = ProcessingStatus | ReviewState;

const styles: Record<BadgeStatus, string> = {
  UPLOADED: "bg-slate-100 text-slate-600",
  VALIDATING: "bg-blue-50 text-blue-700",
  EXTRACTING: "bg-blue-50 text-blue-700",
  SYNCHRONIZING: "bg-blue-50 text-blue-700",
  PROCESSING: "bg-blue-50 text-blue-700",
  PASS_1: "bg-blue-50 text-blue-700",
  PASS_2: "bg-indigo-50 text-indigo-700",
  COMPLETED: "bg-emerald-50 text-emerald-700",
  FAILED: "bg-red-50 text-red-700",
  DRAFT: "bg-slate-100 text-slate-600",
  IN_REVIEW: "bg-amber-50 text-amber-700",
  APPROVED: "bg-emerald-50 text-emerald-700",
  REJECTED: "bg-red-50 text-red-700",
};

const labels: Record<BadgeStatus, string> = {
  UPLOADED: "Uploaded",
  VALIDATING: "Validating",
  EXTRACTING: "Extracting",
  SYNCHRONIZING: "Synchronizing",
  PROCESSING: "Processing",
  PASS_1: "Pass 1",
  PASS_2: "Pass 2",
  COMPLETED: "Completed",
  FAILED: "Failed",
  DRAFT: "Draft",
  IN_REVIEW: "In review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

export function StatusBadge({ status }: { status: BadgeStatus }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-extrabold uppercase tracking-[0.04em] ${styles[status]}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{labels[status]}</span>;
}
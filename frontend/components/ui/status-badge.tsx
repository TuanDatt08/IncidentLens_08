import type { ProcessingStatus, ReviewState } from "@/types/incident";

type BadgeStatus = ProcessingStatus | ReviewState;

const styles: Record<BadgeStatus, string> = {
  UPLOADED: "bg-slate-100 text-slate-600",
  READY: "bg-slate-100 text-slate-600",
  PROCESSING: "bg-blue-50 text-blue-700",
  COMPLETED: "bg-emerald-50 text-emerald-700",
  FAILED: "bg-red-50 text-red-700",
  DRAFT: "bg-amber-50 text-amber-800",
  IN_REVIEW: "bg-sky-100 text-sky-800",
  APPROVED: "bg-teal-100 text-teal-800",
  REJECTED: "bg-red-50 text-red-700",
};

const labels: Record<BadgeStatus, string> = {
  UPLOADED: "Uploaded",
  READY: "Ready",
  PROCESSING: "Processing",
  COMPLETED: "Analysis complete",
  FAILED: "Failed",
  DRAFT: "Not reviewed",
  IN_REVIEW: "In review",
  APPROVED: "Reviewed",
  REJECTED: "Rejected",
};

export function StatusBadge({ status }: { status: BadgeStatus }) {
  return <span data-status={status} className={`status-badge inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium ${styles[status]}`}><span className="h-1 w-1 rounded-full bg-current" />{labels[status]}</span>;
}

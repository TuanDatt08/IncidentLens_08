"use client";

import { useState } from "react";
import { Check, CircleAlert, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { approveReport, rejectReport, submitReport } from "@/services/report.service";
import type { IncidentDraft } from "@/types/incident";

type Action = "submit" | "approve" | "reject";

export function WorkflowActions({ id, draft, onUpdated }: { id: string; draft: IncidentDraft; onUpdated: (draft: IncidentDraft) => void }) {
  const [dialog, setDialog] = useState<Action>();
  const [reason, setReason] = useState("");
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState("");

  async function confirmAction() {
    if (!dialog || (dialog === "submit" ? draft.review_status !== "DRAFT" : draft.review_status !== "IN_REVIEW")) {
      setError("This action is no longer available for the report's review status.");
      return;
    }
    if (dialog === "reject" && !reason.trim()) {
      setError("A rejection reason is required.");
      return;
    }
    setIsWorking(true);
    setError("");
    try {
      const response = dialog === "submit" ? await submitReport(id) : dialog === "approve" ? await approveReport(id) : await rejectReport(id, reason.trim());
      onUpdated({ ...draft, review_status: response.status, version: response.version, ...(response.rejection_reason ? { rejection_reason: response.rejection_reason } : {}) });
      setDialog(undefined);
      setReason("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The workflow action failed.");
    } finally {
      setIsWorking(false);
    }
  }

  if (draft.review_status === "APPROVED") return <div className="flex items-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-5 py-4"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-white"><Check className="h-4 w-4" /></span><div><p className="text-sm font-extrabold text-emerald-900">Report approved</p><p className="mt-0.5 text-xs font-semibold text-emerald-700">This report is now read-only.</p></div></div>;
  if (draft.review_status === "REJECTED") return <div className="flex items-center gap-3 rounded-2xl border border-red-100 bg-red-50 px-5 py-4"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-white"><CircleAlert className="h-4 w-4" /></span><div><p className="text-sm font-extrabold text-red-900">Report rejected</p><p className="mt-0.5 text-xs font-semibold text-red-700">This report is now read-only.</p></div></div>;

  return <><div className="section-card flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center sm:px-6"><div><p className="text-sm font-extrabold text-vf-navy">Report workflow</p><p className="mt-1 text-xs font-semibold text-slate-400">{draft.review_status === "DRAFT" ? "Save your edits, then send the report for review." : "A reviewer needs to make a final decision."}</p></div><div className="flex flex-col gap-2 sm:flex-row">{draft.review_status === "DRAFT" && <Button onClick={() => setDialog("submit")}><span>Submit for Review</span><span aria-hidden>→</span></Button>}{draft.review_status === "IN_REVIEW" && <><Button variant="danger" onClick={() => setDialog("reject")}><X className="h-4 w-4" /> Reject</Button><Button onClick={() => setDialog("approve")}><Check className="h-4 w-4" /> Approve</Button></>}</div></div>{dialog && <ConfirmationDialog action={dialog} reason={reason} setReason={setReason} isWorking={isWorking} error={error} onClose={() => { setDialog(undefined); setError(""); }} onConfirm={confirmAction} />}</>;
}

function ConfirmationDialog({ action, reason, setReason, isWorking, error, onClose, onConfirm }: { action: Action; reason: string; setReason: (value: string) => void; isWorking: boolean; error: string; onClose: () => void; onConfirm: () => void }) {
  const isReject = action === "reject";
  const title = action === "submit" ? "Submit report for review?" : action === "approve" ? "Approve this report?" : "Reject this report?";
  const description = action === "submit" ? "The report will become read-only while it is in review." : action === "approve" ? "The report will be marked approved and become read-only." : "The report will be marked rejected and become read-only.";
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-vf-navy/35 p-5 backdrop-blur-[2px]"><div role="dialog" aria-modal="true" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div className={`flex h-10 w-10 items-center justify-center rounded-xl ${isReject ? "bg-red-50 text-red-600" : "bg-blue-50 text-vf-primary"}`}>{isReject ? <CircleAlert className="h-5 w-5" /> : <Check className="h-5 w-5" />}</div><button type="button" onClick={onClose} aria-label="Close dialog" className="icon-button h-8 w-8"><X className="h-4 w-4" /></button></div><h2 className="mt-5 text-lg font-extrabold text-vf-navy">{title}</h2><p className="mt-2 text-sm font-semibold leading-6 text-slate-500">{description}</p>{isReject && <div className="mt-5"><label htmlFor="rejection-reason" className="field-label">Reason for rejection</label><textarea id="rejection-reason" value={reason} onChange={(event) => setReason(event.target.value)} rows={4} placeholder="Add feedback for the engineer" className="w-full resize-y rounded-xl border border-slate-200 px-3.5 py-3 text-sm font-semibold text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary" /></div>}{error && <p className="mt-4 text-xs font-bold text-red-600">{error}</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button variant={isReject ? "danger" : "primary"} onClick={onConfirm} disabled={isWorking || (isReject && !reason.trim())}>{isWorking ? "Working…" : action === "submit" ? "Submit" : action === "approve" ? "Approve" : "Reject"}</Button></div></div></div>;
}

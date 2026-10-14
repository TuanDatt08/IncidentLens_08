"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Check, CircleAlert, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { useUnsavedChanges } from "@/lib/use-unsaved-changes";
import { approveReport, rejectReport, submitReport } from "@/services/report.service";
import type { IncidentDraft } from "@/types/incident";

import type { EditorState } from "./report-editor";

type Action = "submit" | "approve" | "reject";

export function WorkflowActions({ id, draft, onUpdated, editorState }: { id: string; draft: IncidentDraft; onUpdated: (draft: IncidentDraft) => void; editorState: EditorState }) {
  const { can, status } = useAuth();
  const [dialog, setDialog] = useState<Action>();
  const [reason, setReason] = useState("");
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState("");
  const requestInFlight = useRef(false);
  useEffect(() => {
    if (status === "authenticated") setError("");
  }, [status]);
  const submitBlocked = editorState.dirty || editorState.saving;
  useUnsavedChanges(false, isWorking);

  async function confirmAction() {
    if (requestInFlight.current) return;
    if (dialog === "submit" && submitBlocked) {
      setError(editorState.saving ? "Wait for your changes to finish saving before submitting." : "Save your edits before submitting for review.");
      return;
    }
    if (!dialog || !can(`report:${dialog}`) || (dialog === "submit" ? draft.review_status !== "DRAFT" : draft.review_status !== "IN_REVIEW")) {
      setError("This action is no longer available for the report's review status.");
      return;
    }
    if (dialog === "reject" && !reason.trim()) {
      setError("A rejection reason is required.");
      return;
    }
    requestInFlight.current = true;
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
      requestInFlight.current = false;
      setIsWorking(false);
    }
  }

  if (draft.review_status === "APPROVED") return <div className="report-workflow flex items-center gap-2 border border-emerald-100 bg-emerald-50"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-white"><Check className="h-4 w-4" /></span><div><p className="text-sm font-extrabold text-emerald-900">Report approved</p><p className="mt-0.5 text-xs font-semibold text-emerald-700">This report is now read-only.</p></div></div>;
  if (draft.review_status === "REJECTED") return <div className="report-workflow flex items-center gap-2 border border-red-100 bg-red-50"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-white"><CircleAlert className="h-4 w-4" /></span><div><p className="text-sm font-extrabold text-red-900">Report rejected</p><p className="mt-0.5 text-xs font-semibold text-red-700">This report is now read-only.</p></div></div>;

  return <><div className="report-workflow flex flex-wrap items-center justify-between gap-2"><div><p className="sr-only">Report workflow</p><p className="text-xs font-semibold text-slate-500">{draft.review_status === "DRAFT" ? editorState.saving ? "Saving changes. Wait before submitting." : editorState.dirty ? "You have unsaved edits. Save your changes before submitting." : can("report:submit") ? "Save your edits, then send the report for review." : "An authorized engineer can prepare and submit this draft." : can("report:approve") || can("report:reject") ? "Review the evidence before recording your decision." : "Awaiting a decision from an authorized reviewer."}</p></div><div className="flex flex-wrap gap-2">{draft.review_status === "DRAFT" && can("report:submit") && <Button disabled={submitBlocked || isWorking} onClick={() => setDialog("submit")}><span>Submit for Review</span><span aria-hidden>→</span></Button>}{draft.review_status === "IN_REVIEW" && <>{can("report:reject") && <Button variant="danger" disabled={isWorking} onClick={() => setDialog("reject")}><X className="h-4 w-4" /> Reject</Button>}{can("report:approve") && <Button disabled={isWorking} onClick={() => setDialog("approve")}><Check className="h-4 w-4" /> Approve</Button>}</>}</div></div>{dialog && <ConfirmationDialog action={dialog} reason={reason} setReason={setReason} isWorking={isWorking} error={error} onClose={() => { if (requestInFlight.current) return; setDialog(undefined); setError(""); }} onConfirm={confirmAction} />}</>;
}

function ConfirmationDialog({ action, reason, setReason, isWorking, error, onClose, onConfirm }: { action: Action; reason: string; setReason: (value: string) => void; isWorking: boolean; error: string; onClose: () => void; onConfirm: () => void }) {
  const { status } = useAuth();
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    const element = dialogRef.current;
    if (status === "authenticated") element?.showModal();
    else element?.close();
    return () => { element?.close(); trigger?.focus(); };
  }, [status]);
  const isReject = action === "reject";
  const title = action === "submit" ? "Submit report for review?" : action === "approve" ? "Approve this report?" : "Reject this report?";
  const description = action === "submit" ? "The report will become read-only while it is in review." : action === "approve" ? "The report will be marked approved and become read-only." : "The report will be marked rejected and become read-only.";
  return <dialog ref={dialogRef} aria-labelledby="workflow-dialog-title" aria-describedby="workflow-dialog-description" onCancel={(event) => { event.preventDefault(); if (!isWorking) onClose(); }} className="w-[calc(100%-2rem)] max-w-md rounded-2xl bg-white p-6 shadow-2xl backdrop:bg-vf-navy/35"><div className="flex items-start justify-between gap-4"><div className={`flex h-10 w-10 items-center justify-center rounded-xl ${isReject ? "bg-red-50 text-red-600" : "bg-blue-50 text-vf-primary"}`}>{isReject ? <CircleAlert className="h-5 w-5" /> : <Check className="h-5 w-5" />}</div><button type="button" disabled={isWorking} onClick={onClose} aria-label="Close dialog" className="icon-button h-8 w-8"><X className="h-4 w-4" /></button></div><h2 id="workflow-dialog-title" className="mt-5 text-lg font-extrabold text-vf-navy">{title}</h2><p id="workflow-dialog-description" className="mt-2 text-sm font-semibold leading-6 text-slate-500">{description}</p>{isReject && <div className="mt-5"><label htmlFor="rejection-reason" className="field-label">Reason for rejection</label><textarea id="rejection-reason" disabled={isWorking} value={reason} onChange={(event) => setReason(event.target.value)} rows={4} placeholder="Add feedback for the engineer" className="w-full resize-y rounded-xl border border-slate-200 px-3.5 py-3 text-sm font-semibold text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary" /></div>}{error && <p className="mt-4 text-xs font-bold text-red-600">{error}</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={onClose} disabled={isWorking}>Cancel</Button><Button variant={isReject ? "danger" : "primary"} onClick={onConfirm} disabled={isWorking || (isReject && !reason.trim())}>{isWorking ? "Working…" : action === "submit" ? "Submit" : action === "approve" ? "Approve" : "Reject"}</Button></div></dialog>;
}

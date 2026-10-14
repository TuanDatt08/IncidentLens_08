"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { exportFilename, normalizeReport, printableReport, reportDocx, type ExportDocument } from "@/lib/report-export";
import { prepareReportFigures } from "@/lib/report-visuals";
import { getIncidentTelemetry } from "@/services/telemetry.service";
import type { Evidence } from "@/types/evidence";

type Format = "PDF" | "JSON" | "DOCX";
type Snapshot = { report: unknown; document: ExportDocument; dirty: boolean };

export function ReportExport({ id, report, dirty = false, evidence }: { id: string; report: unknown; dirty?: boolean; evidence?: Evidence[] }) {
  const { status } = useAuth();
  const [snapshot, setSnapshot] = useState<Snapshot>();
  const [format, setFormat] = useState<Format>("PDF");
  const [error, setError] = useState("");
  const [printing, setPrinting] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const preparation = useRef<AbortController>();
  const preparationTimeout = useRef<ReturnType<typeof setTimeout>>();
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const printFrame = useRef<HTMLIFrameElement>();
  const printCleanup = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!snapshot || status !== "authenticated") return;
    const element = dialog.current;
    element?.showModal();
    return () => { element?.close(); if (opener.current?.isConnected) opener.current.focus({ preventScroll: true }); };
  }, [snapshot, status]);
  useEffect(() => {
    if (status !== "authenticated") { preparation.current?.abort(); if (preparationTimeout.current) clearTimeout(preparationTimeout.current); setPreparing(false); setSnapshot(undefined); printFrame.current?.remove(); printFrame.current = undefined; setPrinting(false); }
  }, [status]);
  useEffect(() => () => { preparation.current?.abort(); if (preparationTimeout.current) clearTimeout(preparationTimeout.current); printFrame.current?.remove(); if (printCleanup.current) clearTimeout(printCleanup.current); }, []);

  async function openPreview() {
    if (preparing || status !== "authenticated") return;
    opener.current = document.activeElement as HTMLElement | null;
    const controller = new AbortController(); preparation.current = controller; setPreparing(true);
    preparationTimeout.current = setTimeout(() => { if (preparation.current !== controller) return; controller.abort(); setPreparing(false); setError("Export preparation timed out. Retry when media is available."); }, 20000);
    try {
      const saved = structuredClone(report);
      const document = normalizeReport(id, saved);
      if (evidence !== undefined) {
        const telemetry = await getIncidentTelemetry(id, controller.signal).catch(() => undefined);
        const visuals = await prepareReportFigures(id, evidence, telemetry, controller.signal);
        document.figures = visuals.figures;
        document.sections.push({ title: "Export coverage", lines: visuals.notes });
      }
      if (controller.signal.aborted) return;
      setSnapshot({ report: saved, document, dirty });
      setFormat("PDF"); setError("");
    } catch { if (!controller.signal.aborted) setError("The saved report could not be prepared for export."); }
    finally { if (preparation.current === controller) { if (preparationTimeout.current) clearTimeout(preparationTimeout.current); preparation.current = undefined; setPreparing(false); } }
  }
  function download() {
    if (!snapshot || status !== "authenticated") return;
    try {
      const blob = format === "JSON" ? new Blob([JSON.stringify(snapshot.report, null, 2)], { type: "application/json;charset=utf-8" }) : new Blob([reportDocx(snapshot.document)], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
      const url = URL.createObjectURL(blob); const link = document.createElement("a");
      link.href = url; link.download = exportFilename(id, format.toLowerCase());
      document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      setError("");
    } catch { setError("The file could not be created. Please try again."); }
  }
  function print() {
    if (!snapshot || printing || status !== "authenticated") return;
    printFrame.current?.remove(); if (printCleanup.current) clearTimeout(printCleanup.current);
    const activeControl = dialog.current?.querySelector<HTMLElement>("[data-report-print]") ?? document.activeElement as HTMLElement | null;
    const previewDialog = dialog.current;
    const frame = document.createElement("iframe"); printFrame.current = frame;
    frame.title = "Printable report"; frame.setAttribute("aria-hidden", "true");
    frame.style.cssText = "position:fixed;left:-10000px;top:0;width:794px;height:1123px;border:0";
    const cleanup = () => {
      frame.remove();
      if (printFrame.current === frame) {
        printFrame.current = undefined; setPrinting(false);
        requestAnimationFrame(() => {
          if (previewDialog?.isConnected && previewDialog.open) {
            window.focus();
            if (activeControl?.isConnected && previewDialog.contains(activeControl)) activeControl.focus({ preventScroll: true });
            else previewDialog.querySelector<HTMLElement>("button")?.focus({ preventScroll: true });
          }
        });
      }
    };
    setPrinting(true); setError("");
    frame.onload = async () => {
      try {
        await frame.contentDocument?.fonts.ready;
        if (printFrame.current !== frame || !frame.isConnected) return;
        const target = frame.contentWindow;
        if (!target) throw new Error("Print frame unavailable");
        target.addEventListener("afterprint", cleanup, { once: true });
        target.focus(); target.print();
        if (printFrame.current === frame) printCleanup.current = setTimeout(cleanup, 60000);
      } catch { cleanup(); setError("Printing could not open. Try again or use JSON or DOCX."); }
    };
    frame.srcdoc = printableReport(snapshot.document);
    document.body.appendChild(frame);
  }

  return <>
    <Button variant="ghost" onClick={() => void openPreview()} disabled={status !== "authenticated" || preparing}>{preparing ? "Preparing report…" : "Export report"}</Button>
    {preparing && <Button variant="ghost" onClick={() => { preparation.current?.abort(); if (preparationTimeout.current) clearTimeout(preparationTimeout.current); setPreparing(false); }}>Cancel export</Button>}
    {!snapshot && error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {snapshot && <dialog ref={dialog} aria-labelledby="report-preview-title" aria-describedby="report-preview-note" onCancel={() => setSnapshot(undefined)} className="report-export-dialog w-[calc(100%-2rem)] max-w-4xl rounded-2xl border border-slate-200 bg-slate-50 p-0 text-vf-navy shadow-2xl backdrop:bg-slate-950/60">
      <div className="report-export-header flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 p-5">
        <div><p className="eyebrow">Saved report export</p><h2 id="report-preview-title" className="mt-1 text-xl font-bold">Report preview</h2><p className="mt-1 break-all text-xs text-slate-600">{id} / Version {snapshot.document.version} / {snapshot.document.status}</p></div>
        <Button autoFocus variant="ghost" onClick={() => setSnapshot(undefined)}>Close preview</Button>
      </div>
      <div className="space-y-4 p-5">
        <p id="report-preview-note" className="text-sm text-slate-600">Export uses the saved report shown below. PDF/DOCX may include up to four accessible frame images and two synchronized telemetry charts. Full video files are excluded; JSON contains the saved report only.</p>
        {snapshot.dirty && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Unsaved edits are excluded. Close this preview and save your changes to include them.</p>}
        {format !== "JSON" && snapshot.document.figures?.map((figure, index) => <figure key={index} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3"><Image unoptimized src={`data:image/png;base64,${figure.pngBase64}`} alt={figure.caption} width={figure.width} height={figure.height} className="h-auto max-h-80 w-full object-contain" /><figcaption className="break-words text-xs text-slate-600">Figure {index + 1}. {figure.caption}</figcaption></figure>)}
        <nav aria-label="Export format" className="flex gap-2">{(["PDF", "JSON", "DOCX"] as const).map((value) => <Button key={value} variant={format === value ? "primary" : "ghost"} aria-pressed={format === value} onClick={() => { setFormat(value); setError(""); }}>{value}</Button>)}</nav>
        {format === "JSON" ? <pre aria-label="JSON preview" className="report-export-preview max-h-[50dvh] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-white p-5 text-xs leading-6">{JSON.stringify(snapshot.report, null, 2)}</pre> : <article aria-label="Document preview" className="report-export-preview max-h-[50dvh] overflow-auto rounded-xl border border-slate-200 bg-white p-5 sm:p-8">
          <h3 className="text-2xl font-bold">Incident report</h3><p className="mt-2 break-all text-sm">Report: {id}</p><p className="mt-1 text-xs text-slate-600">Version {snapshot.document.version} / Review status {snapshot.document.status}</p><p className="mt-1 text-xs text-slate-600">Exported: {snapshot.document.exportedAt}</p>
          {snapshot.document.status !== "APPROVED" && <p className="mt-3 text-sm font-bold text-amber-800">UNAPPROVED REPORT</p>}
          {snapshot.document.sections.map((section) => <section key={section.title} className="mt-6"><h4 className="border-b border-slate-200 pb-2 font-bold">{section.title}</h4>{section.lines.map((line, index) => <p key={index} className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">{line}</p>)}</section>)}
        </article>}
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <div className="report-export-footer flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-lg text-xs leading-5 text-slate-600">{format === "PDF" ? "Choose Save as PDF in your browser's print dialog. Page breaks and margins appear in the print preview." : format === "DOCX" ? "Downloads an editable Word document from this saved report." : "Downloads the complete saved report as structured JSON."}</p>
          <Button data-report-print={format === "PDF" ? "true" : undefined} aria-disabled={format === "PDF" && printing} onClick={format === "PDF" ? print : download}>{format === "PDF" ? printing ? "Opening print…" : "Print / Save PDF" : `Download ${format}`}</Button>
        </div>
      </div>
    </dialog>}
  </>;
}

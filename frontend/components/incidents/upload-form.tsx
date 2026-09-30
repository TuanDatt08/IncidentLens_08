"use client";

import Link from "next/link";
import { ChangeEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, FileText, FileVideo, UploadCloud, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { formatFileSize } from "@/lib/format";
import { uploadIncident } from "@/services/incident.service";

const MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024;

export function UploadForm() {
  const router = useRouter();
  const videoInput = useRef<HTMLInputElement>(null);
  const logInput = useRef<HTMLInputElement>(null);
  const [video, setVideo] = useState<File | undefined>();
  const [log, setLog] = useState<File | undefined>();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleVideo(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    const isMp4 = selected.type === "video/mp4" || selected.name.toLowerCase().endsWith(".mp4");
    if (!isMp4) {
      setError("Please select an MP4 video file.");
      return;
    }
    if (selected.size > MAX_VIDEO_SIZE) {
      setError("The video must be smaller than 2 GB.");
      return;
    }
    setError("");
    setVideo(selected);
  }

  function handleLog(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setError("The telemetry log must be a CSV file.");
      return;
    }
    setError("");
    setLog(selected);
  }

  async function handleSubmit() {
    if (!video) {
      setError("An MP4 video is required to create an incident.");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const response = await uploadIncident({ video, log });
      router.push(`/incidents/${response.incident_id}/processing`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed. Please try again.");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-[960px]">
      <Link href="/incidents" className="mb-8 inline-flex items-center gap-2 text-xs font-extrabold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link>
      <div className="mb-8"><p className="eyebrow">New analysis package</p><h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em] text-vf-navy sm:text-4xl">Create Incident</h1><p className="mt-2 text-sm leading-6 text-slate-500">Upload a dashcam video and optional vehicle telemetry log.</p></div>

      <div className="section-card p-5 sm:p-8">
        <div className="mb-7 flex items-start gap-4 border-b border-slate-100 pb-6"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-vf-primary"><UploadCloud className="h-6 w-6" /></span><div><h2 className="font-extrabold text-vf-navy">Incident media</h2><p className="mt-1 text-xs font-semibold leading-5 text-slate-400">The video is required for AI analysis. A matching CSV log improves timeline synchronization.</p></div></div>
        <div className="grid gap-5 lg:grid-cols-2">
          <FileDropzone label="Video" hint="MP4 · required" file={video} inputRef={videoInput} onChange={handleVideo} accept="video/mp4,.mp4" required icon={<FileVideo className="h-6 w-6" />} onRemove={() => { setVideo(undefined); if (videoInput.current) videoInput.current.value = ""; }} />
          <FileDropzone label="Vehicle telemetry log" hint="CSV · optional" file={log} inputRef={logInput} onChange={handleLog} accept=".csv,text/csv" icon={<FileText className="h-6 w-6" />} onRemove={() => { setLog(undefined); if (logInput.current) logInput.current.value = ""; }} />
        </div>
        {error && <div className="mt-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">{error}</div>}
        <div className="mt-8 flex flex-col-reverse justify-end gap-3 border-t border-slate-100 pt-6 sm:flex-row"><Link href="/incidents" className="inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-sm font-extrabold text-slate-500 transition hover:bg-slate-100 hover:text-vf-navy">Cancel</Link><Button disabled={!video || isSubmitting} onClick={handleSubmit}>{isSubmitting ? "Uploading…" : "Create Incident"}<span aria-hidden>→</span></Button></div>
      </div>
      <div className="mt-5 flex items-start gap-3 rounded-xl bg-blue-50/70 px-4 py-3 text-xs font-semibold leading-5 text-blue-800"><Check className="mt-0.5 h-4 w-4 shrink-0" /><span>After upload, IncidentLens validates the package and runs localization before generating the draft report.</span></div>
    </div>
  );
}

function FileDropzone({ label, hint, file, inputRef, onChange, accept, required = false, icon, onRemove }: { label: string; hint: string; file?: File; inputRef: React.RefObject<HTMLInputElement>; onChange: (event: ChangeEvent<HTMLInputElement>) => void; accept: string; required?: boolean; icon: React.ReactNode; onRemove: () => void }) {
  return <div><div className="mb-2 flex items-center justify-between"><label className="field-label mb-0">{label} {required && <span className="text-vf-primary">*</span>}</label><span className="text-[10px] font-bold text-slate-400">{hint}</span></div><input ref={inputRef} type="file" accept={accept} onChange={onChange} className="sr-only" /><button type="button" onClick={() => inputRef.current?.click()} className={`flex min-h-[190px] w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed px-5 text-center transition ${file ? "border-blue-200 bg-blue-50/40" : "border-slate-200 bg-slate-50/70 hover:border-vf-primary hover:bg-blue-50/30"}`}><span className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl ${file ? "bg-vf-primary text-white" : "bg-white text-vf-primary shadow-soft"}`}>{file ? <Check className="h-6 w-6" /> : icon}</span>{file ? <><span className="max-w-full truncate text-sm font-extrabold text-vf-navy">{file.name}</span><span className="mt-1 text-xs font-semibold text-slate-400">{formatFileSize(file.size)} · Ready to upload</span></> : <><span className="text-sm font-extrabold text-vf-navy">Drop your file here</span><span className="mt-1 text-xs font-semibold text-slate-400">or click to browse from your computer</span></>}</button>{file && <button type="button" onClick={onRemove} className="mt-2 inline-flex items-center gap-1 text-xs font-extrabold text-slate-400 transition hover:text-red-600"><X className="h-3.5 w-3.5" /> Remove file</button>}</div>;
}

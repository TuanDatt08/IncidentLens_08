"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { ArrowLeft, Check, FileText, FileVideo, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { formatFileSize } from "@/lib/format";
import { uploadIncident } from "@/services/incident.service";

const MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024;

export function UploadForm() {
  const { can } = useAuth();
  const router = useRouter();
  const videoInput = useRef<HTMLInputElement>(null);
  const logInput = useRef<HTMLInputElement>(null);
  const [video, setVideo] = useState<File | undefined>();
  const [log, setLog] = useState<File | undefined>();
  const [videoError, setVideoError] = useState("");
  const [logError, setLogError] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState<{ loaded: number; total?: number }>({ loaded: 0 });
  const [waiting, setWaiting] = useState(false);
  const [notice, setNotice] = useState("");
  const request = useRef<AbortController>();
  useEffect(() => () => {
    const active = request.current;
    request.current = undefined;
    active?.abort();
  }, []);

  function cancelUpload() {
    const active = request.current;
    if (!active) return;
    request.current = undefined;
    active.abort();
    setIsSubmitting(false); setWaiting(false); setProgress({ loaded: 0 }); setError("");
    setNotice("Upload cancelled. Your files are still selected.");
  }

  function validateVideo(selected: File): string {
    const isMp4 = selected.type === "video/mp4" || selected.name.toLowerCase().endsWith(".mp4");
    if (!isMp4) return "Please select an MP4 video file.";
    if (selected.size > MAX_VIDEO_SIZE) return "The video must be smaller than 2 GB.";
    return "";
  }

  function selectVideo(selected?: File) {
    if (!selected || request.current) return;
    const validationError = validateVideo(selected);
    if (validationError) {
      setVideoError(validationError);
      if (videoInput.current) videoInput.current.value = "";
      return;
    }
    setVideoError(""); setError(""); setNotice("");
    setVideo(selected);
  }

  function handleVideo(event: ChangeEvent<HTMLInputElement>) { selectVideo(event.target.files?.[0]); }

  function selectLog(selected?: File) {
    if (!selected || request.current) return;
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setLogError("The telemetry log must be a CSV file.");
      if (logInput.current) logInput.current.value = "";
      return;
    }
    setLogError(""); setError(""); setNotice("");
    setLog(selected);
  }

  function handleLog(event: ChangeEvent<HTMLInputElement>) { selectLog(event.target.files?.[0]); }

  async function handleSubmit() {
    if (!can("incident:create") || request.current) return;
    if (!video) {
      setError("An MP4 video is required to create an incident.");
      return;
    }
    const active = new AbortController();
    request.current = active;
    const isCurrent = () => request.current === active && !active.signal.aborted;
    setIsSubmitting(true); setWaiting(false); setProgress({ loaded: 0 });
    setError(""); setNotice("");
    let navigating = false;
    try {
      const response = await uploadIncident({ video, log }, {
        signal: active.signal,
        onProgress: (loaded, total) => { if (isCurrent()) setProgress({ loaded, total }); },
        onUploaded: () => { if (isCurrent()) setWaiting(true); },
      });
      if (!isCurrent()) return;
      router.push(`/incidents/${response.incident_id}/processing`);
      navigating = true;
    } catch (reason) {
      if (isCurrent()) setError(reason instanceof Error ? reason.message : "Upload failed. Please try again.");
    } finally {
      if (request.current === active && !navigating) { request.current = undefined; setIsSubmitting(false); setWaiting(false); }
    }
  }

  const percent = progress.total ? Math.min(100, Math.floor(progress.loaded / progress.total * 100)) : undefined;

  return (
    <div className="task-page upload-page mx-auto max-w-[1120px]">
      <Link href="/incidents" onClick={cancelUpload} className="task-back"><ArrowLeft className="h-4 w-4" /> Back to incidents</Link>
      <PageHeader title="Create an incident" description="Bring your video and telemetry together. Upload first, then start analysis when ready." />

      <ol className="upload-journey" aria-label="Incident workflow"><li aria-current="step"><span>01</span> Upload files</li><li><span>02</span> Run analysis</li><li><span>03</span> Review evidence</li></ol>
      <div className="upload-layout">
      <div className="section-card upload-sources">
        <div className="upload-section-heading"><span className="upload-section-number">01</span><div><h2>Source files</h2><p>Choose a video to begin. Add telemetry when available.</p></div></div>
        <div className="grid gap-6">
          <FileDropzone disabled={isSubmitting} id="incident-video" label="Video" hint="MP4 · required" error={videoError} file={video} inputRef={videoInput} onChange={handleVideo} onFileDrop={selectVideo} accept="video/mp4,.mp4" required icon={<FileVideo className="h-6 w-6" />} onRemove={() => { if (request.current) return; setVideo(undefined); setVideoError(""); if (videoInput.current) videoInput.current.value = ""; }} />
          <FileDropzone disabled={isSubmitting} id="incident-telemetry" label="Telemetry log" hint="CSV · optional" error={logError} file={log} inputRef={logInput} onChange={handleLog} onFileDrop={selectLog} accept=".csv,text/csv" icon={<FileText className="h-6 w-6" />} onRemove={() => { if (request.current) return; setLog(undefined); setLogError(""); if (logInput.current) logInput.current.value = ""; }} />
        </div>
        </div>
      <aside className="section-card upload-summary" aria-label="Upload summary">
        <span className="upload-summary-icon"><FileVideo className="h-6 w-6" /></span>
        <h2>Your incident package</h2><p className="upload-summary-description">Check your files before creating the incident.</p>
        <dl className="upload-file-summary"><div><dt>Video <span>Required</span></dt><dd>{video ? <><Check className="h-4 w-4" /><span title={video.name}>{video.name}</span></> : "No file selected"}</dd></div><div><dt>Telemetry <span>Optional</span></dt><dd>{log ? <><Check className="h-4 w-4" /><span title={log.name}>{log.name}</span></> : "No file selected"}</dd></div></dl>
        {error && <div role="alert" className="mt-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">{error}</div>}
        {isSubmitting && <div className="mt-5 space-y-2">
          <p role="status" className="text-sm font-semibold text-slate-600">{waiting ? "Upload sent. Waiting for server response…" : `Uploading ${video?.name}: ${percent === undefined ? formatFileSize(progress.loaded) + " sent" : percent + "%"}`}</p>
          <progress aria-label="File upload progress" max={100} value={percent} className="h-2 w-full" />
        </div>}
        {notice && <p role="status" className="mt-5 text-sm text-slate-600">{notice}</p>}
        <div className="upload-actions"><Button disabled={!video || isSubmitting || !can("incident:create")} onClick={handleSubmit}>{isSubmitting ? waiting ? "Waiting for server…" : "Uploading…" : "Create Incident"}<span aria-hidden>→</span></Button><Button variant="ghost" onClick={() => { if (request.current) cancelUpload(); else router.push("/incidents"); }}>{isSubmitting ? "Cancel upload" : "Cancel"}</Button></div>
        <p className="upload-next-step">Next: check the package status and choose <strong>Start analysis</strong>.</p>
      </aside>
      </div>
    </div>
  );
}

function FileDropzone({ id, label, hint, error, file, inputRef, onChange, onFileDrop, accept, required = false, disabled = false, icon, onRemove }: { id: string; label: string; hint: string; error: string; file?: File; inputRef: React.RefObject<HTMLInputElement>; onChange: (event: ChangeEvent<HTMLInputElement>) => void; onFileDrop: (file?: File) => void; accept: string; required?: boolean; disabled?: boolean; icon: React.ReactNode; onRemove: () => void }) {
  const [dragging, setDragging] = useState(false);
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  function handleDrop(event: React.DragEvent<HTMLButtonElement>) {
    event.preventDefault(); setDragging(false);
    if (!disabled) onFileDrop(event.dataTransfer.files[0]);
  }
  return <div onDragEnter={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }}>
    <div className="mb-2 flex items-center justify-between"><label htmlFor={id} className="field-label mb-0">{label} {required && <span className="text-vf-primary">*</span>}</label><span id={hintId} className="text-[10px] font-bold text-slate-400">{hint}</span></div>
    <input id={id} ref={inputRef} disabled={disabled} tabIndex={-1} required={required} aria-describedby={error ? `${hintId} ${errorId}` : hintId} aria-invalid={!!error} type="file" accept={accept} onChange={onChange} className="sr-only" />
    <button disabled={disabled} type="button" aria-label={`Choose ${label} file`} aria-describedby={error ? `${hintId} ${errorId}` : hintId} onClick={() => { if (!disabled) inputRef.current?.click(); }} onDrop={handleDrop} data-required={required} data-selected={!!file} data-dragging={dragging} className="upload-dropzone">
      <span className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl ${file ? "bg-vf-primary text-white" : "bg-white text-vf-primary shadow-soft"}`}>{file ? <Check className="h-6 w-6" /> : icon}</span>
      {file ? <><span className="max-w-full truncate text-sm font-extrabold text-vf-navy">{file.name}</span><span className="mt-1 text-xs font-semibold text-slate-400">{formatFileSize(file.size)} · Ready to upload</span></> : <><span className="text-sm font-extrabold text-vf-navy">Drop {label.toLowerCase()} here</span><span className="mt-2 text-xs text-slate-400">or click to browse</span><span className="mt-4 text-xs text-slate-400">{required ? "MP4 · up to 2 GB" : "CSV · optional"}</span></>}
    </button>
    {error && <p id={errorId} role="alert" className="mt-2 text-sm font-semibold text-red-700">{error}</p>}
    {file && <button disabled={disabled} type="button" onClick={() => { if (!disabled) onRemove(); }} className="mt-2 inline-flex items-center gap-1 text-xs font-extrabold text-slate-400 transition hover:text-red-600 disabled:opacity-50"><X className="h-3.5 w-3.5" /> Remove file</button>}
  </div>;
}

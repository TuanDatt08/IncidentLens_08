"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { clearUploadResume, uploadRecording, v2Error } from "@/services/v2.service";

export function RecordingUpload({ onComplete }: { onComplete: () => void }) {
  const [file, setFile] = useState<File>();
  const [id, setId] = useState("");
  const [hash, setHash] = useState("");
  const [working, setWorking] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const controller = useRef<AbortController>();
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => () => {
    const active = controller.current;
    controller.current = undefined;
    active?.abort();
  }, []);

  function cancelUpload() {
    const active = controller.current;
    if (!active) return;
    controller.current = undefined;
    active.abort();
    setWorking(false);
    setProgress({ done: 0, total: 0 });
    setError("");
    setNotice("Upload paused. Select the same file and recording ID to resume.");
  }

  function chooseFile(next?: File) {
    if (controller.current) return;
    const replaced = file && (!next || file.name !== next.name || file.size !== next.size || file.lastModified !== next.lastModified);
    if (replaced) clearUploadResume(id);
    setFile(next);
    setHash("");
    setProgress({ done: 0, total: 0 });
    setError("");
    setNotice("");
  }

  function removeFile() {
    if (controller.current) return;
    chooseFile(undefined);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!file || controller.current) return;
    const requestFile = file;
    const requestId = id;
    const requestHash = hash;
    const active = new AbortController();
    controller.current = active;
    setWorking(true); setError(""); setNotice("");
    setProgress({ done: 0, total: 0 });
    const isCurrent = () => controller.current === active && !active.signal.aborted;
    try {
      await uploadRecording(requestFile, requestId, requestHash, (done, total) => {
        if (isCurrent()) setProgress({ done, total });
      }, active.signal);
      if (!isCurrent()) return;
      setNotice("Recording uploaded. Open it from the list to start analysis.");
      onComplete();
    } catch (cause) {
      if (isCurrent()) setError(v2Error(cause));
    } finally {
      if (controller.current === active) {
        controller.current = undefined;
        setWorking(false);
      }
    }
  }
  return <form onSubmit={upload} className="section-card space-y-4 p-5 sm:p-6">
    <h2 className="text-xl font-bold text-vf-navy">Upload a recording</h2>
    <p className="text-sm text-slate-600">Uploads resume after a pause or reload. Select the same file and recording ID.</p>
    <label className="block text-sm font-semibold">Recording ID<input required maxLength={64} disabled={working} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base" value={id} onChange={(event) => setId(event.target.value)} /></label>
    <label className="block text-sm font-semibold">MP4 video<input ref={fileInput} required disabled={working} type="file" accept="video/mp4,.mp4" className="mt-2 block w-full text-base" onChange={(event) => chooseFile(event.target.files?.[0])} /></label>
    {file && <div className="flex flex-wrap items-center justify-between gap-3 text-sm"><p className="break-all text-slate-600">Selected file: <span className="font-semibold text-vf-navy">{file.name}</span></p><Button type="button" variant="ghost" disabled={working} onClick={removeFile}>Remove file</Button></div>}
    <label className="block text-sm font-semibold">Video SHA-256 checksum<input required pattern="[a-f0-9]{64}" disabled={working} aria-describedby="checksum-help" className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base" value={hash} onChange={(event) => setHash(event.target.value.trim().toLowerCase())} /></label>
    <p id="checksum-help" className="text-sm text-slate-600">Use the checksum supplied with your source recording. The server verifies the complete file.</p>
    {working && <p role="status" className="text-sm">Uploading {file?.name}: {progress.done} of {progress.total} parts.</p>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-slate-600">{notice}</p>}
    <div className="flex flex-wrap gap-3"><Button disabled={working || !file} type="submit">Upload or resume</Button>{working && <Button type="button" variant="ghost" onClick={cancelUpload}>Cancel upload</Button>}</div>
  </form>;
}

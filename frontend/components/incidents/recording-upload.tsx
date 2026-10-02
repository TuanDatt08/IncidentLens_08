"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadRecording, v2Error } from "@/services/v2.service";

export function RecordingUpload({ onComplete }: { onComplete: () => void }) {
  const [file, setFile] = useState<File>();
  const [id, setId] = useState("");
  const [hash, setHash] = useState("");
  const [working, setWorking] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [error, setError] = useState("");
  const controller = useRef<AbortController>();
  useEffect(() => () => controller.current?.abort(), []);
  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    controller.current = new AbortController();
    setWorking(true); setError("");
    try {
      await uploadRecording(file, id, hash, (done, total) => setProgress({ done, total }), controller.current.signal);
      onComplete();
    } catch (cause) { setError(v2Error(cause)); }
    finally { setWorking(false); }
  }
  return <form onSubmit={upload} className="section-card space-y-4 p-5 sm:p-6">
    <h2 className="text-xl font-bold text-vf-navy">Upload a recording</h2>
    <p className="text-sm text-slate-600">Uploads resume after a pause or reload. Select the same file and recording ID.</p>
    <label className="block text-sm font-semibold">Recording ID<input required maxLength={64} disabled={working} className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base" value={id} onChange={(event) => setId(event.target.value)} /></label>
    <label className="block text-sm font-semibold">MP4 video<input required type="file" accept="video/mp4,.mp4" disabled={working} className="mt-2 block w-full text-base" onChange={(event) => setFile(event.target.files?.[0])} /></label>
    <label className="block text-sm font-semibold">Video SHA-256 checksum<input required pattern="[a-f0-9]{64}" disabled={working} aria-describedby="checksum-help" className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-base" value={hash} onChange={(event) => setHash(event.target.value.trim().toLowerCase())} /></label>
    <p id="checksum-help" className="text-sm text-slate-600">Use the checksum supplied with your source recording. The server verifies the complete file.</p>
    {working && <p role="status" className="text-sm">Uploaded {progress.done} of {progress.total} parts.</p>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap gap-3"><Button disabled={working} type="submit">Upload or resume</Button>{working && <Button type="button" variant="ghost" onClick={() => controller.current?.abort()}>Pause upload</Button>}</div>
  </form>;
}

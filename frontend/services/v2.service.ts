import { ApiError, parseApiError } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/config";
import type { UploadV2 } from "@/types/v2";

export const V2_BASE_URL = process.env.NEXT_PUBLIC_API_V2_BASE_URL ?? API_BASE_URL.replace(/\/api\/v1\/?$/, "/api/v2");

export async function v2Request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof Blob)) headers.set("Content-Type", "application/json");
  headers.set("X-Requested-With", "IncidentLens");
  const response = await fetch(V2_BASE_URL + path, { ...init, headers, credentials: "include", cache: "no-store" });
  if (!response.ok) throw await parseApiError(response);
  return response.json() as Promise<T>;
}

export function v2Error(cause: unknown): string {
  if (cause instanceof ApiError) {
    if (cause.status === 401) return "Your session is missing or expired. Sign in again, then retry.";
    if (cause.status === 403) return "This action is unavailable for your role or the evidence privacy state.";
    if (cause.status === 409) return "The item changed or an analysis is already active. Refresh before trying again; your edits have been kept.";
    return cause.message;
  }
  return cause instanceof Error ? cause.message : "Request failed. Check your connection and retry.";
}

async function sha256(blob: Blob): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await blob.arrayBuffer())), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function clearUploadResume(recordingId: string): void {
  localStorage.removeItem(`incidentlens:v2:upload:${recordingId}`);
  localStorage.removeItem(`incidentlens:v2:upload-meta:${recordingId}`);
}

function throwIfAborted(signal: AbortSignal): void {
  if (signal.aborted) throw new DOMException("Upload cancelled.", "AbortError");
}

export async function uploadRecording(file: File, recordingId: string, wholeHash: string, onProgress: (done: number, total: number) => void, signal: AbortSignal): Promise<void> {
  const key = `incidentlens:v2:upload:${recordingId}`;
  const metadataKey = `incidentlens:v2:upload-meta:${recordingId}`;
  throwIfAborted(signal);
  let saved = localStorage.getItem(key);
  if (saved) {
    let matches = false;
    try {
      const previous = JSON.parse(localStorage.getItem(metadataKey) ?? "null") as { upload_id?: string; bytes?: number; sha256?: string } | null;
      matches = previous?.upload_id === saved && previous.bytes === file.size && previous.sha256 === wholeHash;
    } catch {
      // Unknown metadata cannot prove that the saved session uses this checksum.
    }
    if (!matches) {
      clearUploadResume(recordingId);
      saved = null;
    }
  }
  let upload: UploadV2;
  if (saved) {
    try {
      upload = await v2Request<UploadV2>(`/uploads/${encodeURIComponent(saved)}`, { signal });
      throwIfAborted(signal);
    }
    catch (cause) {
      if (cause instanceof ApiError && (cause.status === 404 || cause.code === "UPLOAD_EXPIRED")) {
        throwIfAborted(signal);
        if (localStorage.getItem(key) === saved) {
          localStorage.removeItem(key);
          localStorage.removeItem(metadataKey);
        }
        throw new Error("The saved upload expired or is unavailable. Click Upload or resume again to start a new session.");
      }
      throw cause;
    }
  } else {
    upload = await v2Request<UploadV2>("/uploads", { method: "POST", signal, body: JSON.stringify({ recording_id: recordingId, filename: file.name, bytes: file.size, media_type: "video/mp4", sha256: wholeHash, part_size: 8 * 1024 * 1024 }) });
    throwIfAborted(signal);
    localStorage.setItem(key, upload.upload_id);
    localStorage.setItem(metadataKey, JSON.stringify({ upload_id: upload.upload_id, bytes: file.size, sha256: wholeHash }));
  }
  throwIfAborted(signal);
  const done = new Set(upload.parts.map((part) => part.number));
  onProgress(done.size, upload.part_count);
  for (let number = 1; number <= upload.part_count; number++) {
    throwIfAborted(signal);
    if (done.has(number)) continue;
    const part = file.slice((number - 1) * upload.part_size, number * upload.part_size);
    const digest = await sha256(part);
    throwIfAborted(signal);
    await v2Request(`/uploads/${upload.upload_id}/parts/${number}`, { method: "PUT", signal, headers: { "X-Part-SHA256": digest }, body: part });
    throwIfAborted(signal);
    done.add(number);
    onProgress(done.size, upload.part_count);
  }
  await v2Request(`/uploads/${upload.upload_id}/complete`, { method: "POST", signal });
  throwIfAborted(signal);
  if (localStorage.getItem(key) === upload.upload_id) {
    localStorage.removeItem(key);
    const metadata = localStorage.getItem(metadataKey);
    if (metadata && (JSON.parse(metadata) as { upload_id?: string }).upload_id === upload.upload_id) localStorage.removeItem(metadataKey);
  }
}

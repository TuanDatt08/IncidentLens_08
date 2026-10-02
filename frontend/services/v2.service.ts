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

export async function uploadRecording(file: File, recordingId: string, wholeHash: string, onProgress: (done: number, total: number) => void, signal: AbortSignal): Promise<void> {
  const key = `incidentlens:v2:upload:${recordingId}`;
  const saved = localStorage.getItem(key);
  let upload: UploadV2;
  if (saved) {
    try { upload = await v2Request<UploadV2>(`/uploads/${encodeURIComponent(saved)}`, { signal }); }
    catch (cause) {
      if (cause instanceof ApiError && (cause.status === 404 || cause.code === "UPLOAD_EXPIRED")) {
        localStorage.removeItem(key);
        throw new Error("The saved upload expired or is unavailable. Click Upload or resume again to start a new session.");
      }
      throw cause;
    }
  } else {
    upload = await v2Request<UploadV2>("/uploads", { method: "POST", signal, body: JSON.stringify({ recording_id: recordingId, filename: file.name, bytes: file.size, media_type: "video/mp4", sha256: wholeHash, part_size: 8 * 1024 * 1024 }) });
    localStorage.setItem(key, upload.upload_id);
  }
  const done = new Set(upload.parts.map((part) => part.number));
  onProgress(done.size, upload.part_count);
  for (let number = 1; number <= upload.part_count; number++) {
    if (signal.aborted) throw new DOMException("Upload paused; reselect this file to resume.", "AbortError");
    if (done.has(number)) continue;
    const part = file.slice((number - 1) * upload.part_size, number * upload.part_size);
    const digest = await sha256(part);
    await v2Request(`/uploads/${upload.upload_id}/parts/${number}`, { method: "PUT", signal, headers: { "X-Part-SHA256": digest }, body: part });
    done.add(number);
    onProgress(done.size, upload.part_count);
  }
  await v2Request(`/uploads/${upload.upload_id}/complete`, { method: "POST", signal });
  localStorage.removeItem(key);
}

import { apiFetch } from "./api-client";
import type { Evidence } from "@/types/evidence";
import type { TelemetryChart } from "@/types/telemetry";
import type { ExportFigure } from "./report-export";

export async function prepareReportFigures(id: string, evidence: Evidence[], telemetry: TelemetryChart | undefined, signal: AbortSignal) {
  const figures: ExportFigure[] = [];
  const notes: string[] = [];
  const frames = evidence.filter(item => item.kind === "frame" && item.media_type === "image/jpeg").slice(0, 4);
  if (!frames.length) notes.push("No accessible JPEG frame evidence was available for embedding.");
  for (const item of frames) {
    if (signal.aborted) throw new DOMException("Export cancelled", "AbortError");
    try {
      const response = await apiFetch(`/incidents/${encodeURIComponent(id)}/evidence/${encodeURIComponent(item.evidence_id)}/media`, { signal });
      if (!response.ok) throw new Error("Evidence unavailable");
      if (Number(response.headers.get("content-length")) > 4 * 1024 * 1024) throw new Error("Image exceeds export budget");
      const blob = await response.blob();
      if (blob.size > 4 * 1024 * 1024 || !blob.type.startsWith("image/")) throw new Error("Invalid evidence image");
      const url = URL.createObjectURL(blob);
      try {
        const image = new Image(); image.src = url; await image.decode();
        if (signal.aborted) throw new DOMException("Export cancelled", "AbortError");
        if (image.naturalWidth * image.naturalHeight > 16000000) throw new Error("Image dimensions exceed export budget");
        const canvas = document.createElement("canvas");
        const scale = Math.min(1, 1000 / image.naturalWidth, 750 / image.naturalHeight);
        canvas.width = Math.max(1, Math.round(image.naturalWidth * scale)); canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
        const context = canvas.getContext("2d"); if (!context) throw new Error("Canvas unavailable");
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        figures.push({ caption: `${item.evidence_id} at ${item.time_range_s[0]}s (incident-relative); SHA256 ${item.sha256}`, pngBase64: canvas.toDataURL("image/png").split(",")[1], width: canvas.width, height: canvas.height });
      } finally { URL.revokeObjectURL(url); }
    } catch (error) {
      if (signal.aborted) throw error;
      notes.push(`Image ${item.evidence_id} was not embedded because it could not be read within the export budget.`);
    }
  }
  if (evidence.filter(item => item.kind === "frame").length > frames.length) notes.push("At most four frame images are embedded; the evidence registry lists the remaining assets.");
  if (!telemetry || telemetry.state !== "available" || telemetry.alignment !== "VERIFIED" || telemetry.time_basis !== "video_seconds") {
    notes.push("Telemetry charts are omitted because synchronized video-time telemetry is unavailable.");
  } else {
    for (const series of telemetry.signals.slice(0, 2)) {
      const points = series.samples.filter(point => Number.isFinite(point.time_s));
      const valid = points.filter(point => point.value !== null && Number.isFinite(point.value));
      if (valid.length < 2) continue;
      const canvas = document.createElement("canvas"); canvas.width = 1000; canvas.height = 360;
      const context = canvas.getContext("2d"); if (!context) continue;
      const minT = Math.min(...valid.map(p => p.time_s)), maxT = Math.max(...valid.map(p => p.time_s));
      const minV = Math.min(...valid.map(p => p.value!)), maxV = Math.max(...valid.map(p => p.value!));
      if (maxT <= minT) continue;
      context.fillStyle = "white"; context.fillRect(0, 0, 1000, 360);
      context.font = "20px Arial"; context.fillStyle = "#111";
      context.fillText(`${series.label} (${series.unit ?? "unit not supplied"})`, 70, 32);
      context.font = "16px Arial"; context.fillText(`${minT.toFixed(2)} – ${maxT.toFixed(2)} video seconds`, 360, 340);
      context.fillText(maxV.toFixed(2), 8, 72); context.fillText(minV.toFixed(2), 8, 290);
      context.strokeStyle = "#aaa"; context.strokeRect(70, 60, 900, 230);
      context.strokeStyle = "#2255aa"; context.lineWidth = 2; context.beginPath(); let connected = false;
      for (const point of points) {
        if (point.value === null || !Number.isFinite(point.value)) { connected = false; continue; }
        const x = 70 + (point.time_s - minT) / (maxT - minT) * 900;
        const y = 290 - (point.value - minV) / Math.max(maxV - minV, 1e-9) * 230;
        if (connected) context.lineTo(x, y); else context.moveTo(x, y);
        connected = true;
      }
      context.stroke();
      figures.push({ caption: `${series.label}; source: telemetry; alignment VERIFIED; ${telemetry.downsampled ? "downsampled" : "supplied"} samples. Charts do not by themselves establish a collision.`, pngBase64: canvas.toDataURL("image/png").split(",")[1], width: 1000, height: 360 });
    }
  }
  return { figures, notes };
}

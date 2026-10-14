import type { AnalysisCoverage } from "@/types/incident";

export function AnalysisCoverageSection({ coverage }: { coverage: AnalysisCoverage }) {
  const available = coverage.state === "available";
  const times = coverage.sampled_timestamps_s;
  const count = coverage.sampled_frame_count;
  const duration = coverage.duration_s;
  const frameSummary = count !== null && Number.isFinite(count) && count >= 0 ? `${count} frames inspected` : "Frame count unknown";
  const durationSummary = duration !== null && Number.isFinite(duration) && duration >= 0 ? `${duration.toFixed(2)}s video` : "Video duration unknown";
  const alignment = coverage.telemetry_alignment.trim();
  const limitations = [...new Set(coverage.limitations.map((item) => item.trim()).filter(Boolean))];
  return <section className="section-card space-y-4 p-5 sm:p-6" aria-label="Analysis coverage">
    <h2 className="text-lg font-semibold text-vf-navy">Analysis scope</h2>
    <p className="text-sm text-slate-600">{available ? `${frameSummary} · ${durationSummary}` : "Analysis scope is unknown. Inspection data is unavailable."}</p>
    <p className="text-sm leading-6 text-amber-800">{available ? "Sample-based analysis may miss events between frames or outside inspected windows." : "Missing inspection data cannot establish that the entire video is safe."}</p>
    <details className="analysis-coverage-details text-sm text-slate-600">
      <summary className="cursor-pointer py-2 font-medium text-vf-navy">Analysis details</summary>
      <div className="mt-2 space-y-3 leading-6">
        <p className="break-words">Video timestamps: {times.length ? times.map((time) => `${time.toFixed(2)}s`).join(", ") : "Unknown"}.</p>
        <p>Telemetry alignment: {!alignment || alignment.toUpperCase() === "UNKNOWN" ? "Unknown" : alignment}.</p>
        {limitations.length > 0 && <details>
          <summary className="cursor-pointer py-2 font-medium text-vf-navy">Technical notes</summary>
          <ul className="mt-2 list-disc space-y-2 break-words pl-5">{limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </details>}
      </div>
    </details>
  </section>;
}

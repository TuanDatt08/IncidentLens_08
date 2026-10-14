import type { IncidentDraft } from "@/types/incident";

export function IncidentTimeline({ draft, onSeek, seekEnabled }: { draft: IncidentDraft; onSeek: (seconds: number) => void; seekEnabled: boolean }) {
  const window = draft.incident_window;
  if (!window) return <section className="section-card p-5 sm:p-6"><h2 className="text-lg font-semibold text-vf-navy">Incident Timeline</h2><p className="mt-5 text-sm font-semibold text-slate-500">No incident window is available.</p></section>;

  const min = Math.min(0, window.start);
  const max = Math.max(0, window.end);
  const span = Math.max(1, max - min);
  const position = (value: number) => ((value - min) / span) * 100;
  const startPosition = position(window.start);
  const criticalPosition = position(window.critical);
  const endPosition = position(window.end);

  return <section className="section-card p-5 sm:p-6"><div className="flex items-end justify-between gap-4"><div><h2 className="text-lg font-semibold text-vf-navy">Incident Timeline</h2></div></div><div className="mt-4 px-5"><div className="incident-timeline-rail relative h-11"><div className="absolute top-1/2 h-[3px] w-full -translate-y-1/2 rounded-full bg-slate-500/20" /><div className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-teal-400/35" style={{ left: `${startPosition}%`, width: `${endPosition - startPosition}%` }} /><TimelineMarker label="START" value={window.start} position={startPosition} onSeek={onSeek} seekEnabled={seekEnabled} /><TimelineMarker label="CRITICAL" value={window.critical} position={criticalPosition} onSeek={onSeek} seekEnabled={seekEnabled} critical /><TimelineMarker label="END" value={window.end} position={endPosition} onSeek={onSeek} seekEnabled={seekEnabled} /></div><div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500"><span>Start <span className="mt-1 block font-medium tabular-nums text-vf-navy">{formatRelativeTime(window.start)}</span></span><span className="text-center">Critical <span className="mt-1 block font-medium tabular-nums text-vf-navy">{formatRelativeTime(window.critical)}</span></span><span className="text-right">End <span className="mt-1 block font-medium tabular-nums text-vf-navy">{formatRelativeTime(window.end)}</span></span></div></div></section>;
}

function formatRelativeTime(value: number): string { return `${value.toFixed(1)}s`; }

function TimelineMarker({ label, value, position, onSeek, seekEnabled, critical = false }: { label: string; value: number; position: number; onSeek: (seconds: number) => void; seekEnabled: boolean; critical?: boolean }) {
  return <button type="button" aria-label={`${label} ${formatRelativeTime(value)}`} title={`${label} ${formatRelativeTime(value)}`} disabled={!seekEnabled} onClick={() => onSeek(value)} className="absolute top-1/2 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-lg transition hover:bg-teal-400/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-300 disabled:cursor-not-allowed disabled:opacity-40" style={{ left: `${position}%` }}><span className={`block h-2 w-2 rounded-full ring-2 ring-slate-400/20 ${critical ? "bg-amber-200/80" : "bg-teal-300/80"}`} /></button>;
}

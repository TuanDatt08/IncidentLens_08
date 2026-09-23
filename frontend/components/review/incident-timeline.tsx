import type { IncidentDraft } from "@/types/incident";

export function IncidentTimeline({ draft, onSeek, seekEnabled }: { draft: IncidentDraft; onSeek: (seconds: number) => void; seekEnabled: boolean }) {
  const window = draft.incident_window;
  if (!window) return <section className="section-card p-5 sm:p-6"><p className="eyebrow">Video context</p><h2 className="mt-2 text-xl font-extrabold tracking-[-0.03em] text-vf-navy">Incident Timeline</h2><p className="mt-5 text-sm font-semibold text-slate-500">No incident window is available.</p></section>;

  const min = Math.min(0, window.start);
  const max = Math.max(0, window.end);
  const span = Math.max(1, max - min);
  const position = (value: number) => ((value - min) / span) * 100;
  const startPosition = position(window.start);
  const criticalPosition = position(window.critical);
  const endPosition = position(window.end);

  return <section className="section-card p-5 sm:p-6"><div className="flex items-end justify-between gap-4"><div><p className="eyebrow">Video context</p><h2 className="mt-2 text-xl font-extrabold tracking-[-0.03em] text-vf-navy">Incident Timeline</h2></div><span className="text-xs font-bold text-slate-400">{formatRelativeTime(min)} — {formatRelativeTime(max)}</span></div><div className="mt-9 px-1"><div className="relative h-8"><div className="absolute top-1/2 h-1.5 w-full -translate-y-1/2 rounded-full bg-slate-100" /><div className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-blue-200" style={{ left: `${startPosition}%`, width: `${endPosition - startPosition}%` }} /><TimelineMarker label="START" value={window.start} position={startPosition} onSeek={onSeek} seekEnabled={seekEnabled} /><TimelineMarker label="CRITICAL" value={window.critical} position={criticalPosition} onSeek={onSeek} seekEnabled={seekEnabled} critical /><TimelineMarker label="END" value={window.end} position={endPosition} onSeek={onSeek} seekEnabled={seekEnabled} /></div><div className="mt-5 flex justify-between text-[10px] font-extrabold text-slate-400"><span>{formatRelativeTime(min)}</span><span>{formatRelativeTime((min + max) / 2)}</span><span>{formatRelativeTime(max)}</span></div></div><div className="mt-6 grid grid-cols-3 gap-3 border-t border-slate-100 pt-5"><TimelineStat label="Start" value={window.start} /><TimelineStat label="Critical" value={window.critical} critical /><TimelineStat label="End" value={window.end} /></div></section>;
}

function formatRelativeTime(value: number): string { return `${value.toFixed(1)}s`; }

function TimelineMarker({ label, value, position, onSeek, seekEnabled, critical = false }: { label: string; value: number; position: number; onSeek: (seconds: number) => void; seekEnabled: boolean; critical?: boolean }) {
  return <button type="button" disabled={!seekEnabled} onClick={() => onSeek(value)} className="group absolute top-1/2 -translate-x-1/2 -translate-y-1/2 disabled:cursor-not-allowed disabled:opacity-50" style={{ left: `${position}%` }}><span className={`block h-4 w-4 rounded-full border-4 border-white shadow ${critical ? "bg-amber-500 ring-4 ring-amber-100" : "bg-vf-primary"}`} /><span className={`absolute bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap text-[9px] font-extrabold tracking-[0.09em] transition ${critical ? "text-amber-600" : "text-vf-primary"}`}>{label}</span><span className="absolute left-1/2 top-7 -translate-x-1/2 whitespace-nowrap text-[10px] font-bold text-slate-400 opacity-0 transition group-hover:opacity-100">{formatRelativeTime(value)}</span></button>;
}

function TimelineStat({ label, value, critical = false }: { label: string; value: number; critical?: boolean }) { return <div className="text-center"><p className={`text-[10px] font-extrabold uppercase tracking-[0.1em] ${critical ? "text-amber-600" : "text-slate-400"}`}>{label}</p><p className="mt-1 text-sm font-extrabold text-vf-navy">{formatRelativeTime(value)}</p></div>; }

import { CircleAlert, Clock, Gauge, Lock } from "@/components/icons";
import type { IncidentDraft } from "@/types/incident";
import { StatusBadge } from "@/components/ui/status-badge";

export function IncidentSummary({ draft }: { draft: IncidentDraft }) {
  const window = draft.incident_window;
  return <section className="section-card p-5 sm:p-6"><div className="flex items-start justify-between gap-3"><div><p className="eyebrow">AI draft</p><h2 className="mt-2 text-xl font-extrabold tracking-[-0.03em] text-vf-navy">Incident Summary</h2></div><StatusBadge status={draft.review_status} /></div><div className="mt-6 grid grid-cols-2 gap-4 border-b border-slate-100 pb-5"><Metric icon={<CircleAlert className="h-4 w-4" />} label="Incident type" value={draft.incident_type ?? "Not detected"} /><Metric icon={<Gauge className="h-4 w-4" />} label="Incident detected" value={draft.incident_detected ? "Yes" : "No"} /><Metric icon={<Clock className="h-4 w-4" />} label="Incident window" value={window ? `${formatRelativeTime(window.start)} → ${formatRelativeTime(window.end)}` : "Not available"} /><Metric icon={<span className="text-[10px] font-black">C</span>} label="Critical moment" value={window ? formatRelativeTime(window.critical) : "Not available"} critical /></div><div className="pt-5"><p className="field-label">Summary</p><p className="text-sm font-semibold leading-6 text-slate-600">{draft.summary ?? "No summary available."}</p></div>{draft.unknowns.length > 0 && <div className="mt-5 rounded-xl bg-amber-50/80 p-4"><div className="flex items-center gap-2 text-xs font-extrabold text-amber-800"><CircleAlert className="h-4 w-4" /> Unknowns</div><ul className="mt-2 space-y-1 pl-5 text-xs font-semibold leading-5 text-amber-800">{draft.unknowns.map((unknown, index) => <li key={index} className="list-disc">{typeof unknown === "string" ? unknown : JSON.stringify(unknown)}</li>)}</ul></div>}<div className="mt-5 flex items-center gap-2 text-[10px] font-bold text-slate-400"><Lock className="h-3.5 w-3.5" /> Incident metadata is read-only.</div></section>;
}

function formatRelativeTime(value: number): string { return `${value.toFixed(1)}s`; }

function Metric({ icon, label, value, critical = false }: { icon: React.ReactNode; label: string; value: string; critical?: boolean }) {
  return <div><span className={`flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-[0.08em] ${critical ? "text-amber-600" : "text-slate-400"}`}>{icon}{label}</span><p className="mt-1 text-xs font-extrabold text-vf-navy">{value}</p></div>;
}

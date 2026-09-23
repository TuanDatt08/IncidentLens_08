import type { AuditEvent } from "@/types/audit";

export function AuditSection({ events }: { events: AuditEvent[] }) {
  return <section className="section-card p-5 sm:p-6"><div><p className="eyebrow">Traceability</p><h2 className="mt-2 text-xl font-extrabold tracking-[-0.03em] text-vf-navy">Audit history</h2></div>{events.length === 0 ? <p className="mt-5 text-xs font-semibold text-slate-400">No audit events recorded.</p> : <div className="mt-5 divide-y divide-slate-100">{events.map((event) => <div key={event.event_id} className="flex flex-col gap-1 py-3 first:pt-0 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-xs font-extrabold text-vf-navy">{event.action}</p><p className="mt-1 text-[11px] font-semibold text-slate-400">{event.actor} Â· {event.role}</p></div><time className="text-[10px] font-bold text-slate-400">{new Date(event.created_at).toLocaleString()}</time></div>)}</div>}</section>;
}

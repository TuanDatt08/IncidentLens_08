import type { AuditEvent } from "@/types/audit";

export function AuditSection({ events, loading = false, error = "" }: { events: AuditEvent[]; loading?: boolean; error?: string }) {
  return <section className="section-card p-5 sm:p-6" aria-busy={loading}>
    <h2 className="text-xl font-extrabold text-vf-navy">Audit history</h2>
    {loading ? <p role="status" className="mt-4 text-sm text-slate-600">Loading audit history…</p>
      : error ? <p role="alert" className="mt-4 text-sm text-red-700">Audit history could not be loaded: {error}</p>
      : events.length === 0 ? <p className="mt-4 text-sm text-slate-600">No audit events recorded.</p>
      : <ol className="mt-4 divide-y divide-slate-100">{events.map((event) => <li key={event.event_id} className="flex flex-col gap-1 py-3 sm:flex-row sm:justify-between">
        <div><p className="text-sm font-bold text-vf-navy">{event.action}</p><p className="mt-1 text-sm text-slate-600">{event.actor ?? "Unknown actor"}{event.role ? ` · ${event.role}` : ""}</p></div>
        <time dateTime={event.created_at} className="text-sm text-slate-600">{new Date(event.created_at).toLocaleString()}</time>
      </li>)}</ol>}
  </section>;
}

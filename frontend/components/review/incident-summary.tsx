import { CircleAlert } from "@/components/icons";
import type { IncidentDraft } from "@/types/incident";

export function IncidentSummary({ draft }: { draft: IncidentDraft }) {
  const window = draft.incident_window;
  return <section className="section-card p-5 sm:p-6" aria-labelledby="incident-summary-title">
    <h2 id="incident-summary-title" className="text-lg font-semibold text-vf-navy">Analysis summary</h2>
    <p className="mt-3 text-sm leading-7 text-slate-600">{draft.summary || (draft.incident_detected ? "Review the evidence and complete the report below." : "No incident was confirmed in the analyzed frames. This does not establish absence across the entire video.")}</p>
    {(draft.incident_type || window) && <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-4 border-t border-slate-100 pt-4 text-sm">
      {draft.incident_type && <div><dt className="text-xs text-slate-500">Event type</dt><dd className="mt-1 text-vf-navy">{draft.incident_type}</dd></div>}
      {window && <><div><dt className="text-xs text-slate-500">Incident window</dt><dd className="mt-1 text-vf-navy">{window.start.toFixed(1)} → {window.end.toFixed(1)}s</dd></div><div><dt className="text-xs text-slate-500">Critical moment</dt><dd className="mt-1 text-vf-navy">{window.critical.toFixed(1)}s</dd></div></>}
    </dl>}
    {draft.unknowns.length > 0 && <div className="mt-4 rounded-lg bg-amber-50/80 p-4"><h3 className="flex items-center gap-2 text-sm text-amber-800"><CircleAlert className="h-4 w-4" /> Uncertainty & missing evidence</h3><ul className="mt-2 space-y-1 pl-5 text-sm leading-6 text-amber-800">{draft.unknowns.map((unknown, index) => <li key={index} className="list-disc">{typeof unknown === "string" ? unknown : JSON.stringify(unknown)}</li>)}</ul></div>}
  </section>;
}

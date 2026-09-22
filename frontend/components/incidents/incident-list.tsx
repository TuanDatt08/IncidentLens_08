"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, MoreHorizontal, Plus, Search } from "@/components/icons";
import { formatDate } from "@/lib/format";
import { listIncidents } from "@/services/incident.service";
import type { IncidentRecord, ProcessingStatus, ReviewState } from "@/types/incident";
import { StatusBadge } from "@/components/ui/status-badge";

const processingFilters: Array<"ALL" | ProcessingStatus> = ["ALL", "PROCESSING", "COMPLETED", "FAILED"];

export function IncidentList() {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [filter, setFilter] = useState<(typeof processingFilters)[number]>("ALL");
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listIncidents()
      .then((data) => {
        if (active) setIncidents(data);
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const filteredIncidents = useMemo(() => {
    const normalizedSearch = search.toLowerCase().trim();
    return incidents.filter((incident) => {
      const matchesStatus = filter === "ALL" || incident.processing_status === filter;
      const matchesSearch = !normalizedSearch || `${incident.id} ${incident.file_name}`.toLowerCase().includes(normalizedSearch);
      return matchesStatus && matchesSearch;
    });
  }, [filter, incidents, search]);

  const counts = useMemo(() => ({
    all: incidents.length,
    processing: incidents.filter((item) => item.processing_status === "PROCESSING").length,
    completed: incidents.filter((item) => item.processing_status === "COMPLETED").length,
    failed: incidents.filter((item) => item.processing_status === "FAILED").length,
  }), [incidents]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">RAV-18 workspace</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em] text-vf-navy sm:text-4xl">Incidents</h1>
          <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">Review AI-assisted incident analysis packages and manage report approvals.</p>
        </div>
        <Link href="/incidents/new" className="inline-flex h-11 items-center justify-center gap-2 self-start rounded-xl bg-vf-primary px-4 text-sm font-extrabold text-white shadow-[0_7px_15px_rgba(20,100,244,0.18)] transition hover:bg-blue-700 sm:self-auto">
          <Plus className="h-4 w-4" /> Create Incident
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <SummaryStat label="Total incidents" value={counts.all} accent="navy" />
        <SummaryStat label="Processing" value={counts.processing} accent="blue" />
        <SummaryStat label="Completed" value={counts.completed} accent="green" />
        <SummaryStat label="Needs attention" value={counts.failed} accent="red" />
      </div>

      <section className="section-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <div>
            <h2 className="font-extrabold text-vf-navy">Incident packages</h2>
            <p className="mt-1 text-xs font-semibold text-slate-400">Latest uploads and report workflow status</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <label className="relative block">
              <span className="sr-only">Search incidents</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search incidents" className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs font-semibold text-vf-navy outline-none transition placeholder:text-slate-400 focus:border-vf-primary sm:w-44" />
            </label>
            <div className="flex rounded-xl bg-slate-100 p-1">
              {processingFilters.map((item) => <button key={item} type="button" onClick={() => setFilter(item)} className={`rounded-lg px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.04em] transition ${filter === item ? "bg-white text-vf-primary shadow-sm" : "text-slate-500 hover:text-vf-navy"}`}>{item === "ALL" ? "All" : item === "PROCESSING" ? "Active" : item[0] + item.slice(1).toLowerCase()}</button>)}
            </div>
          </div>
        </div>

        {error && <div className="m-5 rounded-xl bg-red-50 px-4 py-3 text-sm font-bold text-red-700">{error}</div>}
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full min-w-[740px] text-left">
            <thead className="bg-slate-50/70 text-[10px] font-extrabold uppercase tracking-[0.13em] text-slate-400">
              <tr><th className="px-7 py-4">Incident</th><th className="px-5 py-4">Created</th><th className="px-5 py-4">Processing</th><th className="px-5 py-4">Report status</th><th className="px-5 py-4" /></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? <LoadingRows /> : filteredIncidents.map((incident) => <IncidentRow key={incident.id} incident={incident} />)}
            </tbody>
          </table>
          {!isLoading && filteredIncidents.length === 0 && <EmptyState />}
        </div>
        <div className="space-y-3 p-4 md:hidden">
          {isLoading ? <div className="h-24 animate-pulse rounded-xl bg-slate-100" /> : filteredIncidents.map((incident) => <IncidentMobileCard key={incident.id} incident={incident} />)}
          {!isLoading && filteredIncidents.length === 0 && <EmptyState />}
        </div>
      </section>
    </div>
  );
}

function SummaryStat({ label, value, accent }: { label: string; value: number; accent: "navy" | "blue" | "green" | "red" }) {
  const colors = { navy: "bg-vf-navy", blue: "bg-vf-primary", green: "bg-emerald-500", red: "bg-red-500" };
  return <div className="section-card flex items-center gap-3 px-4 py-4 sm:px-5"><span className={`h-2.5 w-2.5 rounded-full ${colors[accent]}`} /><div><p className="text-[10px] font-extrabold uppercase tracking-[0.1em] text-slate-400">{label}</p><p className="mt-1 text-xl font-extrabold text-vf-navy">{value.toString().padStart(2, "0")}</p></div></div>;
}

function IncidentRow({ incident }: { incident: IncidentRecord }) {
  return <tr className="group transition hover:bg-slate-50/70"><td className="px-7 py-5"><Link href={`/incidents/${incident.id}`} className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-xs font-extrabold text-vf-primary">R18</span><span><span className="block text-sm font-extrabold text-vf-navy group-hover:text-vf-primary">{incident.id}</span><span className="mt-1 block max-w-[260px] truncate text-xs font-semibold text-slate-400">{incident.file_name}</span></span></Link></td><td className="px-5 py-5 text-xs font-bold text-slate-500">{formatDate(incident.created_at)}</td><td className="px-5 py-5"><StatusBadge status={incident.processing_status} /></td><td className="px-5 py-5"><StatusBadge status={incident.report_status} /></td><td className="px-5 py-5 text-right"><Link href={incident.processing_status === "COMPLETED" ? `/incidents/${incident.id}` : `/incidents/${incident.id}/processing`} className="inline-flex items-center gap-1 text-xs font-extrabold text-vf-primary opacity-80 transition group-hover:opacity-100">View <ArrowRight className="h-3.5 w-3.5" /></Link></td></tr>;
}

function IncidentMobileCard({ incident }: { incident: IncidentRecord }) {
  const destination = incident.processing_status === "COMPLETED" ? `/incidents/${incident.id}` : `/incidents/${incident.id}/processing`;
  return <Link href={destination} className="block rounded-xl border border-slate-100 p-4 transition hover:border-blue-200 hover:bg-blue-50/30"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-extrabold text-vf-navy">{incident.id}</p><p className="mt-1 max-w-[220px] truncate text-xs font-semibold text-slate-400">{incident.file_name}</p></div><MoreHorizontal className="h-5 w-5 text-slate-400" /></div><div className="mt-4 flex flex-wrap items-center gap-2"><StatusBadge status={incident.processing_status} /><StatusBadge status={incident.report_status} /><span className="ml-auto text-[11px] font-bold text-slate-400">{formatDate(incident.created_at)}</span></div></Link>;
}

function LoadingRows() { return <>{[1, 2, 3].map((row) => <tr key={row}><td colSpan={5} className="px-7 py-5"><div className="h-10 animate-pulse rounded-lg bg-slate-100" /></td></tr>)}</>; }
function EmptyState() { return <div className="px-6 py-14 text-center"><p className="font-extrabold text-vf-navy">No incidents found</p><p className="mt-1 text-sm text-slate-400">Try another search or create a new incident package.</p></div>; }
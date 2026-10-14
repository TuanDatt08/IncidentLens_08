"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ArrowRight, FileText, Plus, Search } from "@/components/icons";
import { formatDate } from "@/lib/format";
import { listIncidents } from "@/services/incident.service";
import { loadIncidentReviews, type IncidentReviewSummary } from "@/services/incident-review.service";
import type { IncidentListResponse, IncidentRecord, ProcessingStatus, ReviewState } from "@/types/incident";
import { StatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";

const reviewFilters: { value: "ALL" | ReviewState; label: string }[] = [
  { value: "ALL", label: "All" }, { value: "DRAFT", label: "Not reviewed" },
  { value: "IN_REVIEW", label: "In review" }, { value: "APPROVED", label: "Reviewed" },
  { value: "REJECTED", label: "Rejected" },
];
const processingFilters: Array<"ALL" | ProcessingStatus> = ["ALL", "UPLOADED", "READY", "PROCESSING", "COMPLETED", "FAILED"];

export function IncidentList() {
  const { can } = useAuth();
  const [listing, setListing] = useState<IncidentListResponse>({ items: [], total: 0, limit: 20, offset: 0 });
  const incidents = listing.items;
  const [reviews, setReviews] = useState<Record<string, IncidentReviewSummary>>({});
  const [reviewFilter, setReviewFilter] = useState<"ALL" | ReviewState>("ALL");
  const [filter, setFilter] = useState<"ALL" | ProcessingStatus>("ALL");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    async function load() {
      try {
        const data = await listIncidents(20, offset, controller.signal);
        if (controller.signal.aborted) return;
        setListing(data); setReviews({}); setHasLoaded(true); setError("");
        setIsLoading(false); setReviewLoading(true);
        await loadIncidentReviews(data.items, controller.signal, (id, summary) => {
          setReviews((current) => ({ ...current, [id]: summary }));
        });
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Could not load incidents.");
      } finally {
        if (!controller.signal.aborted) { setIsLoading(false); setReviewLoading(false); }
      }
    }
    void load();
    return () => controller.abort();
  }, [offset, retryCount]);

  const filteredIncidents = useMemo(() => {
    const normalized = search.toLowerCase().trim();
    return incidents.filter((incident) => {
      const review = reviews[incident.incident_id];
      return (filter === "ALL" || incident.processing_status === filter)
        && (reviewFilter === "ALL" || (review?.state === "available" && review.status === reviewFilter))
        && (!normalized || `${incident.incident_id} ${incident.incident_record?.scenario ?? ""}`.toLowerCase().includes(normalized));
    });
  }, [filter, incidents, reviews, reviewFilter, search]);
  const unavailable = Object.values(reviews).some((review) => review.state === "error");
  const actionLabel = can("report:approve") || can("report:reject") ? "Review" : "View";
  const pageProcessing = incidents.filter((incident) => incident.processing_status === "PROCESSING").length;
  const pageReviewCount = (status: ReviewState) => incidents.filter((incident) => {
    const review = reviews[incident.incident_id];
    return review?.state === "available" && review.status === status;
  }).length;

  return <div className="incident-list">
    <PageHeader title="Incidents" description={can("report:approve") ? "Review evidence and decide on reports awaiting review." : can("incident:create") ? "Upload video, track analysis and prepare reports for review." : "Browse evidence and follow report review progress."} action={can("incident:create") && <Link href="/incidents/new" className="workspace-action inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--workspace-primary)] px-4 text-sm font-semibold text-[var(--workspace-on-accent)] transition-colors hover:brightness-110"><Plus className="h-4 w-4" />Upload video</Link>} />
    <section className="investigation-summary" aria-label="Incident overview">
      <div className="summary-stat"><span className="summary-stat-label">Total incidents</span><strong className="summary-stat-value">{isLoading || !hasLoaded || error ? "—" : listing.total}</strong><span className="summary-stat-note">Across your accessible incidents</span></div>
      <div className="summary-stat"><span className="summary-stat-label">Processing</span><strong className="summary-stat-value">{isLoading || !hasLoaded || error ? "—" : pageProcessing}</strong><span className="summary-stat-note">On this page</span></div>
      <div className="summary-stat"><span className="summary-stat-label">In review</span><strong className="summary-stat-value">{isLoading || reviewLoading || !hasLoaded || error || unavailable ? "—" : pageReviewCount("IN_REVIEW")}</strong><span className="summary-stat-note">On this page</span></div>
      <div className="summary-stat"><span className="summary-stat-label">Reviewed</span><strong className="summary-stat-value">{isLoading || reviewLoading || !hasLoaded || error || unavailable ? "—" : pageReviewCount("APPROVED")}</strong><span className="summary-stat-note">On this page</span></div>
    </section>
    <section className="incident-list-surface section-card overflow-hidden" aria-label="Incident packages">
      <div className="incident-review-filters" role="group" aria-label="Filter reports by review status on this page">
        {reviewFilters.map(({ value, label }) => <button key={value} type="button" className="incident-review-filter" aria-pressed={reviewFilter === value} onClick={() => setReviewFilter(value)}>
          {label}<span className="incident-filter-count">{value === "ALL" ? incidents.length : incidents.filter((incident) => { const review = reviews[incident.incident_id]; return review?.state === "available" && review.status === value; }).length}</span>
        </button>)}
      </div>
      <div className="incident-list-tools">
        <label className="incident-list-search relative"><span className="sr-only">Search incidents</span><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search this page" className="pl-9" /></label>
        <label className="incident-list-select"><span>Processing</span><select aria-label="Processing status" value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}>{processingFilters.map((value) => <option key={value} value={value}>{value === "ALL" ? "All processing states" : value === "COMPLETED" ? "Analysis complete" : value[0] + value.slice(1).toLowerCase()}</option>)}</select></label>
        <p className="text-xs text-slate-500">{reviewLoading ? "Loading review states…" : `${filteredIncidents.length} matching on this page`}</p>
      </div>
      {hasLoaded && <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{filteredIncidents.length} matching incidents on this page. {listing.total} incidents total.</p>}
      {isLoading && <p role="status" className="px-5 py-3 text-sm text-slate-500">{hasLoaded ? "Refreshing incidents…" : "Loading incidents…"}</p>}
      {error && <div className="m-5 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-red-50 px-4 py-3"><p role="alert" className="text-sm text-red-700">{error}</p><Button variant="ghost" disabled={isLoading} onClick={() => setRetryCount((count) => count + 1)}>Retry</Button></div>}
      {unavailable && !reviewLoading && <div className="flex flex-wrap items-center justify-between gap-2 bg-amber-50 px-5 py-3 text-sm text-amber-800"><p role="status">Some review states could not be loaded.</p><Button variant="ghost" disabled={isLoading} onClick={() => setRetryCount((count) => count + 1)}>Retry review states</Button></div>}
      <div className="hidden overflow-x-auto lg:block">
        <table className="incident-list-table w-full min-w-[740px] text-left">
          <thead><tr><th className="px-5 py-4">Incident / Report</th><th className="px-4 py-4">Review</th><th className="px-4 py-4">Processing</th><th className="px-4 py-4">Created</th><th className="px-5 py-4"><span className="sr-only">Open report</span></th></tr></thead>
          <tbody>{isLoading && !hasLoaded ? <LoadingRows /> : filteredIncidents.map((incident) => <tr key={incident.incident_id} className="incident-clickable-row">
            <td className="px-5 py-4"><Link href={destination(incident)} aria-label={`${actionLabel} ${incident.incident_id}`} className="incident-row-link"><IncidentName incident={incident} /></Link></td><td className="px-4 py-4"><ReviewStatus incident={incident} review={reviews[incident.incident_id]} pending={reviewLoading} /></td><td className="px-4 py-4"><StatusBadge status={incident.processing_status} /></td><td className="px-4 py-4 text-xs text-slate-500">{formatDate(incident.created_at)}</td>
            <td className="px-5 py-4"><span aria-hidden="true" className="inline-flex items-center gap-1 text-xs font-bold text-vf-primary">{actionLabel}<ArrowRight className="h-4 w-4" /></span></td>
          </tr>)}</tbody>
        </table>
      </div>
      <div className="incident-mobile-list space-y-2 p-3 lg:hidden">{isLoading && !hasLoaded ? <div aria-hidden="true" className="h-24 animate-pulse rounded-lg bg-slate-200" /> : filteredIncidents.map((incident) => <Link key={incident.incident_id} href={destination(incident)} aria-label={`${actionLabel} ${incident.incident_id}`} className="incident-mobile-card block rounded-lg border p-3">
        <IncidentName incident={incident} /><div className="mt-2 flex flex-wrap items-center gap-2"><ReviewStatus incident={incident} review={reviews[incident.incident_id]} pending={reviewLoading} /><StatusBadge status={incident.processing_status} /></div><p className="mt-2 text-xs text-slate-500">{formatDate(incident.created_at)}</p>
      </Link>)}</div>
      {!isLoading && !reviewLoading && hasLoaded && !error && filteredIncidents.length === 0 && <div role="status" className="px-6 py-12 text-center"><p className="font-bold text-vf-navy">{incidents.length ? "No matching incidents" : "No incidents yet"}</p><p className="mt-2 text-sm text-slate-500">{incidents.length ? "Try another search or filter." : can("incident:create") ? "Upload a video to create your first incident." : "Incidents will appear here when they are available in your scope."}</p>{incidents.length > 0 && <Button variant="ghost" className="mt-4" onClick={() => { setSearch(""); setFilter("ALL"); setReviewFilter("ALL"); }}>Clear filters</Button>}</div>}
      <footer className="incident-list-footer flex flex-wrap items-center justify-between gap-3 px-5 py-4 text-xs text-slate-500">
        <div><p>{hasLoaded ? `Showing ${listing.total === 0 ? 0 : listing.offset + 1}–${Math.min(listing.offset + incidents.length, listing.total)} of ${listing.total} incidents` : "Incident totals unavailable"}</p><p className="mt-1">Search, review counts and filters apply to this page.</p></div>
        {listing.total > listing.limit && <div className="flex items-center gap-2"><Button variant="ghost" disabled={isLoading || listing.offset === 0} onClick={() => setOffset(Math.max(0, listing.offset - listing.limit))}>Previous</Button><span>Page {Math.floor(listing.offset / listing.limit) + 1} of {Math.ceil(listing.total / listing.limit)}</span><Button variant="ghost" disabled={isLoading || listing.offset + listing.limit >= listing.total} onClick={() => setOffset(listing.offset + listing.limit)}>Next</Button></div>}
      </footer>
    </section>
  </div>;
}

function destination(incident: IncidentRecord) {
  const path = `/incidents/${encodeURIComponent(incident.incident_id)}`;
  return incident.processing_status === "COMPLETED" ? path : `${path}/processing`;
}
function IncidentName({ incident }: { incident: IncidentRecord }) {
  const scenario = incident.incident_record?.scenario?.replaceAll("_", " ").trim();
  const description = scenario ? incident.incident_id : (incident.video_metadata ? `Video · ${incident.video_metadata.duration.toFixed(1)}s · ${incident.video_metadata.width} × ${incident.video_metadata.height}` : "Video metadata unavailable");
  return <span className="incident-list-name flex items-center gap-3"><span className="incident-list-name-icon flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"><FileText className="h-4 w-4" /></span><span className="incident-list-name-content min-w-0"><span className="incident-list-title block break-words text-sm font-bold">{scenario || incident.incident_id}</span><span className="incident-list-meta mt-1 block max-w-[320px] break-words text-xs">{description}</span></span></span>;
}
function ReviewStatus({ incident, review, pending }: { incident: IncidentRecord; review?: IncidentReviewSummary; pending: boolean }) {
  if (review?.state === "available") return <div className="flex flex-wrap items-center gap-2"><StatusBadge status={review.status} /><span className="text-[11px] text-slate-500">v{review.version}</span></div>;
  return <span className="text-xs text-slate-500">{incident.processing_status !== "COMPLETED" ? "No report yet" : review?.state === "error" ? "Status unavailable" : review?.state === "missing" ? "Report unavailable" : pending ? "Loading…" : "Status unavailable"}</span>;
}
function LoadingRows() { return <>{[1, 2, 3].map((row) => <tr key={row}><td colSpan={5} className="px-5 py-4"><div className="h-10 animate-pulse rounded-lg bg-slate-200" /></td></tr>)}</>; }

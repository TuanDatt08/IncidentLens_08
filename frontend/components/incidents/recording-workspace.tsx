"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { v2Error, v2Request } from "@/services/v2.service";
import type { CandidateV2, JobV2, PageV2, SessionV2 } from "@/types/v2";

export function RecordingWorkspace({ id }: { id: string }) {
  const [candidates, setCandidates] = useState<CandidateV2[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [job, setJob] = useState<JobV2>();
  const [session, setSession] = useState<SessionV2>();
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState("self_hosted");
  const load = useCallback(async () => {
    try {
      const [data, jobs, identity] = await Promise.all([v2Request<PageV2<CandidateV2>>(`/recordings/${encodeURIComponent(id)}/candidates`), v2Request<PageV2<JobV2>>(`/recordings/${encodeURIComponent(id)}/jobs`), v2Request<SessionV2>("/session")]);
      setCandidates(data.items); setCursor(data.next_cursor); setJob(jobs.items[0]); setSession(identity);
    } catch (cause) { setError(v2Error(cause)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (job?.status !== "queued" && job?.status !== "running") return;
    const timer = setTimeout(() => void load(), 2000);
    return () => clearTimeout(timer);
  }, [job, load]);
  async function act(action: "analyze" | "cancel" | "resume") {
    setWorking(true); setError("");
    try {
      if (action === "analyze") await v2Request(`/recordings/${encodeURIComponent(id)}/analyze`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ provider_profile: profile }) });
      else if (job) await v2Request(`/jobs/${job.job_id}/${action}`, { method: "POST" });
      await load();
    } catch (cause) { setError(v2Error(cause)); await load(); }
    finally { setWorking(false); }
  }
  async function more() {
    if (!cursor) return;
    setWorking(true);
    try { const data = await v2Request<PageV2<CandidateV2>>(`/recordings/${encodeURIComponent(id)}/candidates?cursor=${encodeURIComponent(cursor)}`); setCandidates((items) => [...items, ...data.items]); setCursor(data.next_cursor); }
    catch (cause) { setError(v2Error(cause)); }
    finally { setWorking(false); }
  }
  const active = job?.status === "queued" || job?.status === "running";
  return <div className="space-y-6">
    <Link href="/recordings" className="text-sm font-semibold text-vf-primary underline underline-offset-4">Back to recordings</Link>
    <h1 className="break-words text-3xl font-bold text-vf-navy">{id}</h1>
    {loading && <p role="status">Loading candidates and active job…</p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <div className="flex flex-wrap items-end gap-3">
      <Button variant="ghost" onClick={() => { setError(""); void load(); }} disabled={working}>Refresh</Button>
      {session?.roles.includes("Engineer") && <>
        <label className="text-sm font-semibold">Analysis provider<select className="ml-3 rounded-lg border border-slate-300 p-3 text-base" value={profile} disabled={working || active} onChange={(event) => setProfile(event.target.value)}><option value="self_hosted">Internal</option><option value="external_api">External (requires privacy approval)</option></select></label>
        <Button onClick={() => void act("analyze")} disabled={working || active}>Analyze recording</Button>
        {active && <Button variant="ghost" onClick={() => void act("cancel")} disabled={working}>Cancel analysis</Button>}
        {job?.status === "failed" && <Button variant="ghost" onClick={() => void act("resume")} disabled={working}>Resume failed analysis</Button>}
      </>}
    </div>
    {job && <section className="section-card space-y-3 p-5" aria-live="polite">
      <h2 className="text-xl font-bold text-vf-navy">Analysis: {job.status}</h2>
      <p className="text-sm text-slate-700">Stage: {job.stage}. Completed checkpoints: {job.progress.done}. Reserved calls: {job.budget.calls_used}/{job.budget.max_calls}.</p>
      {job.error && <p className="text-sm text-red-700">{job.error.code}: {job.error.message}</p>}
      {!!job.partial_results.filter((result) => result.report_id).length && job.status !== "succeeded" && <p className="text-sm text-amber-800">Partial reports are preserved and available below.</p>}
      {job.coverage.unknowns?.map((unknown, index) => <p key={index} className="text-sm text-slate-600">{unknown}</p>)}
    </section>}
    <section className="section-card p-5 sm:p-6">
      <h2 className="text-xl font-bold text-vf-navy">Candidates</h2>
      {!loading && candidates.length === 0 && <p className="mt-4 text-slate-600">No candidates have been recorded. This does not establish that the whole recording is incident-free.</p>}
      <ul className="mt-4 divide-y divide-slate-200">{candidates.map((candidate) => <li key={candidate.candidate_id} className="flex flex-col justify-between gap-3 py-4 sm:flex-row sm:items-center">
        <div className="min-w-0"><p className="break-words font-semibold text-vf-navy">{candidate.reasons.join(", ")}</p><p className="mt-1 text-sm tabular-nums text-slate-700">{candidate.window.start_s.toFixed(2)}–{candidate.window.end_s.toFixed(2)} video seconds · {candidate.analysis_state}</p>{candidate.analysis_state === "UNANALYZED" && <p className="mt-1 text-sm text-amber-800">Retained for analysis beyond the current budget.</p>}</div>
        {candidate.report_id && <Link className="shrink-0 font-semibold text-vf-primary underline underline-offset-4" href={`/reports/${candidate.report_id}`}>Review report</Link>}
      </li>)}</ul>
      {cursor && <Button onClick={() => void more()} disabled={working}>Load more candidates</Button>}
    </section>
  </div>;
}

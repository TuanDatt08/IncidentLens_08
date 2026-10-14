"use client";

import Link from "next/link";
import { AnalysisProgress } from "./analysis-progress";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { createSerialPoller, type SerialPoller } from "@/lib/serial-poller";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { v2Error, v2Request } from "@/services/v2.service";
import type { CandidateV2, JobV2, PageV2, SessionV2 } from "@/types/v2";

export function RecordingWorkspace({ id }: { id: string }) {
  const [snapshotId, setSnapshotId] = useState(id);
  const [candidates, setCandidates] = useState<CandidateV2[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [job, setJob] = useState<JobV2>();
  const [session, setSession] = useState<SessionV2>();
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [moreError, setMoreError] = useState("");
  const [pollError, setPollError] = useState("");
  const [candidateLoadState, setCandidateLoadState] = useState<"loading" | "error" | "success">("loading");
  const [profile, setProfile] = useState("self_hosted");
  const poller = useRef<SerialPoller>();
  const operation = useRef<AbortController>();
  const busy = useRef(false);
  const loadedMore = useRef(false);
  const candidateSnapshotReady = useRef(false);
  const cancelOperation = useCallback(() => {
    operation.current?.abort();
    operation.current = undefined;
    busy.current = false;
  }, []);
  useEffect(() => {
    let live = true;
    setSnapshotId(id); setLoading(true); setWorking(false); setError(""); setMoreError(""); setPollError(""); setCandidates([]); setCursor(null); setJob(undefined); setSession(undefined); setCandidateLoadState("loading"); loadedMore.current = false; candidateSnapshotReady.current = false;
    const coordinator = createSerialPoller({
      async run(signal) {
        const results = await Promise.allSettled([
          v2Request<PageV2<CandidateV2>>("/recordings/" + encodeURIComponent(id) + "/candidates", { signal }),
          v2Request<PageV2<JobV2>>("/recordings/" + encodeURIComponent(id) + "/jobs", { signal }).then((jobs) => {
            // Job freshness must not wait for slower candidate/session responses.
            if (live && !signal.aborted) setJob(jobs.items[0]);
            return jobs;
          }),
          v2Request<SessionV2>("/session", { signal }),
        ]);
        if (!live || signal.aborted) return "stop";
        setLoading(false);
        const [data, jobs, identity] = results;
        if (data.status === "fulfilled") {
          candidateSnapshotReady.current = true;
          setCandidateLoadState("success");
          setCandidates((items) => mergeCandidates(items, data.value.items));
          if (!loadedMore.current) setCursor(data.value.next_cursor);
        } else if (!candidateSnapshotReady.current) setCandidateLoadState("error");
        if (identity.status === "fulfilled") setSession(identity.value);
        const rejected = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
        const permanent = rejected.find((result) => !retryable(result.reason));
        const failure = permanent ?? rejected[0];
        const latest = jobs.status === "fulfilled" ? jobs.value.items[0] : undefined;
        const authoritativeStop = jobs.status === "fulfilled" && latest?.status !== "queued" && latest?.status !== "running";
        if (authoritativeStop) {
          setPollError(failure ? v2Error(failure.reason) : "");
          return "stop";
        }
        if (failure) throw failure.reason;
        setPollError("");
        return "active";
      },
      shouldRetry: retryable,
      onError(cause) { if (live) { setPollError(v2Error(cause)); if (!candidateSnapshotReady.current) setCandidateLoadState("error"); setLoading(false); } },
    });
    poller.current = coordinator;
    void coordinator.refresh();
    return () => {
      live = false;
      coordinator.stop();
      cancelOperation();
      if (poller.current === coordinator) poller.current = undefined;
    };
  }, [id, cancelOperation]);
  async function act(action: "analyze" | "cancel" | "resume") {
    const coordinator = poller.current;
    if (!coordinator || busy.current) return;
    busy.current = true;
    const controller = new AbortController();
    operation.current = controller;
    setWorking(true); setError("");
    try {
      await coordinator.suspend();
      if (controller.signal.aborted) return;
      if (action === "analyze") await v2Request("/recordings/" + encodeURIComponent(id) + "/analyze", { method: "POST", signal: controller.signal, headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ provider_profile: profile }) });
      else if (job) await v2Request("/jobs/" + job.job_id + "/" + action, { method: "POST", signal: controller.signal });
    } catch (cause) { if (!controller.signal.aborted) setError(v2Error(cause)); }
    finally {
      if (!controller.signal.aborted) {
        await coordinator.resume();
        if (!controller.signal.aborted) { busy.current = false; operation.current = undefined; setWorking(false); }
      }
    }
  }
  async function more() {
    const coordinator = poller.current;
    if (!cursor || !coordinator || busy.current) return;
    busy.current = true;
    const controller = new AbortController();
    operation.current = controller;
    setWorking(true);
    try {
      await coordinator.suspend();
      if (controller.signal.aborted) return;
      const data = await v2Request<PageV2<CandidateV2>>("/recordings/" + encodeURIComponent(id) + "/candidates?cursor=" + encodeURIComponent(cursor), { signal: controller.signal });
      if (!controller.signal.aborted) {
        loadedMore.current = true;
        setCandidates((items) => mergeCandidates(items, data.items));
        setCursor(data.next_cursor);
        setMoreError("");
      }
    } catch (cause) { if (!controller.signal.aborted) setMoreError(v2Error(cause)); }
    finally {
      if (!controller.signal.aborted) {
        await coordinator.resume(false);
        if (!controller.signal.aborted) { busy.current = false; operation.current = undefined; setWorking(false); }
      }
    }
  }
  const sameRecording = snapshotId === id;
  const visibleCandidates = sameRecording ? candidates : [];
  const visibleJob = sameRecording ? job : undefined;
  const visibleSession = sameRecording ? session : undefined;
  const visiblePollError = sameRecording ? pollError : "";
  const visibleError = sameRecording ? error : "";
  const visibleLoading = !sameRecording || loading;
  const active = visibleJob?.status === "queued" || visibleJob?.status === "running";
  return <div className="space-y-6">
    <Link href="/recordings" className="text-sm font-semibold text-vf-primary underline underline-offset-4">Back to recordings</Link>
    <PageHeader title="Recording analysis" context={id} description="Analyze this recording, inspect candidates and open their reports for review." />
    {visibleLoading && <p role="status">Loading candidates and active job…</p>}
    {visiblePollError && <p role="alert" className="text-red-700">{visiblePollError}</p>}
    {visibleError && <p role="alert" className="text-red-700">{visibleError}</p>}
    <div className="flex flex-wrap items-end gap-3">
      <Button variant="ghost" onClick={() => { void poller.current?.refresh(); }} disabled={working}>{visiblePollError ? "Retry" : "Refresh"}</Button>
      {visibleSession?.roles.includes("Engineer") && <>
        <label className="text-sm font-semibold">Analysis provider<select className="ml-3 rounded-lg border border-slate-300 p-3 text-base" value={profile} disabled={working || active} onChange={(event) => setProfile(event.target.value)}><option value="self_hosted">Internal</option><option value="external_api">External (requires privacy approval)</option></select></label>
        <Button onClick={() => void act("analyze")} disabled={working || active}>Analyze recording</Button>
        {active && <Button variant="ghost" onClick={() => void act("cancel")} disabled={working}>Cancel analysis</Button>}
        {job?.status === "failed" && <Button variant="ghost" onClick={() => void act("resume")} disabled={working}>Resume failed analysis</Button>}
      </>}
    </div>
    {visibleJob && <section className="section-card space-y-3 p-5" aria-live="polite">
      <h2 className="text-xl font-bold text-vf-navy">Analysis: {visibleJob.status}</h2>
      <AnalysisProgress key={`${id}:${visibleJob.job_id}`} state={visibleJob.status} paused={!!visiblePollError || working} value={visibleJob.progress.total !== null && Number.isFinite(visibleJob.progress.total) && visibleJob.progress.total > 0 && Number.isFinite(visibleJob.progress.done) ? visibleJob.progress.done / visibleJob.progress.total * 100 : null} />
      <p className="text-sm text-slate-700">Stage: {visibleJob.stage}. Completed checkpoints: {visibleJob.progress.done}. Reserved calls: {visibleJob.budget.calls_used}/{visibleJob.budget.max_calls}.</p>
      {visibleJob.error && <p className="text-sm text-red-700">{visibleJob.error.code}: {visibleJob.error.message}</p>}
      {!!visibleJob.partial_results.filter((result) => result.report_id).length && visibleJob.status !== "succeeded" && <p className="text-sm text-amber-800">Partial reports are preserved and available below.</p>}
      {visibleJob.coverage.unknowns?.map((unknown, index) => <p key={index} className="text-sm text-slate-600">{unknown}</p>)}
    </section>}
    <section className="section-card p-5 sm:p-6">
      <h2 className="text-xl font-bold text-vf-navy">Candidates</h2>
      {sameRecording && moreError && <p role="alert" className="mt-4 text-sm text-red-700">{moreError}</p>}
      {sameRecording && candidateLoadState === "error" && visibleCandidates.length === 0 && <p className="mt-4 text-sm text-slate-600">Candidates could not be loaded. Retry to check again.</p>}
      {sameRecording && candidateLoadState === "success" && visibleCandidates.length === 0 && <p className="mt-4 text-slate-600">No candidates have been recorded. This does not establish that the whole recording is incident-free.</p>}
      <ul className="mt-4 divide-y divide-slate-200">{visibleCandidates.map((candidate) => <li key={candidate.candidate_id} className="flex flex-col justify-between gap-3 py-4 sm:flex-row sm:items-center">
        <div className="min-w-0"><p className="break-words font-semibold text-vf-navy">{candidate.reasons.join(", ")}</p><p className="mt-1 text-sm tabular-nums text-slate-700">{candidate.window.start_s.toFixed(2)}–{candidate.window.end_s.toFixed(2)} video seconds · {candidate.analysis_state}</p>{candidate.analysis_state === "UNANALYZED" && <p className="mt-1 text-sm text-amber-800">Retained for analysis beyond the current budget.</p>}</div>
        {candidate.report_id && <Link className="shrink-0 font-semibold text-vf-primary underline underline-offset-4" href={`/reports/${candidate.report_id}`}>Review report</Link>}
      </li>)}</ul>
      {cursor && <Button onClick={() => void more()} disabled={working}>Load more candidates</Button>}
    </section>
  </div>;
}

function retryable(cause: unknown): boolean {
  return cause instanceof TypeError || cause instanceof ApiError && (cause.status === 408 || cause.status === 429 || cause.status >= 500);
}

function mergeCandidates(existing: CandidateV2[], incoming: CandidateV2[]): CandidateV2[] {
  const merged = [...existing];
  const indexById = new Map(merged.map((candidate, index) => [candidate.candidate_id, index]));
  for (const candidate of incoming) {
    const index = indexById.get(candidate.candidate_id);
    if (index === undefined) {
      indexById.set(candidate.candidate_id, merged.length);
      merged.push(candidate);
    } else {
      merged[index] = candidate;
    }
  }
  return merged;
}

"use client";

import Link from "next/link";
import { V2_WORKSPACE_ENABLED } from "@/lib/config";
import { V2WorkspaceUnavailable } from "@/components/auth/v2-workspace-gate";
import { useCallback, useEffect, useState } from "react";
import { RecordingUpload } from "@/components/incidents/recording-upload";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { v2Error, v2Request } from "@/services/v2.service";
import type { PageV2, SessionV2 } from "@/types/v2";

type Recording = { recording_id: string; duration_s: number };

export default function Recordings() {
  return V2_WORKSPACE_ENABLED ? <EnabledRecordings /> : <V2WorkspaceUnavailable />;
}

function EnabledRecordings() {
  const [items, setItems] = useState<Recording[]>([]);
  const [session, setSession] = useState<SessionV2>();
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async (next?: string) => {
    setLoading(true); setError("");
    try {
      const [data, identity] = await Promise.all([v2Request<PageV2<Recording>>("/recordings" + (next ? `?cursor=${encodeURIComponent(next)}` : "")), v2Request<SessionV2>("/session")]);
      setItems((current) => next ? [...current, ...data.items] : data.items); setCursor(data.next_cursor); setSession(identity);
    } catch (cause) { setError(v2Error(cause)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return <div className="mx-auto max-w-5xl space-y-6">
    <PageHeader title="Recordings" description="Upload recordings, follow analysis and inspect candidate incidents." action={<Button variant="secondary" onClick={() => void load()} disabled={loading}>{loading ? "Refreshing…" : error ? "Retry" : "Refresh"}</Button>} />
    <section className="recording-list" aria-label="Available recordings" aria-busy={loading}>
      {loading && <p role="status" className="recording-list-status">Loading recordings…</p>}
      {error && <p role="alert" className="auth-error m-4">{error}</p>}
      {!loading && !error && items.length === 0 && <div className="recording-list-status"><h2 className="font-semibold">No recordings yet</h2><p className="mt-2 text-sm text-slate-600">{session?.roles.includes("Engineer") ? "Upload a recording below to begin." : "Recordings will appear here when they are available in your scope."}</p></div>}
      <ul>{items.map((item) => <li key={item.recording_id}><Link href={`/recordings/${encodeURIComponent(item.recording_id)}`}><strong>{item.recording_id}</strong><span className="tabular-nums">{item.duration_s.toFixed(1)} seconds <span aria-hidden="true">→</span></span></Link></li>)}</ul>
    </section>
    {cursor && <Button onClick={() => void load(cursor)} disabled={loading}>Load more recordings</Button>}
    {session?.roles.includes("Engineer") && <RecordingUpload onComplete={() => void load()} />}
  </div>;
}

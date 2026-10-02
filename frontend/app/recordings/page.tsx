"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { RecordingUpload } from "@/components/incidents/recording-upload";
import { Button } from "@/components/ui/button";
import { v2Error, v2Request } from "@/services/v2.service";
import type { PageV2, SessionV2 } from "@/types/v2";

type Recording = { recording_id: string; duration_s: number };

export default function Recordings() {
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
    <div className="flex flex-wrap items-center justify-between gap-4"><h1 className="text-3xl font-bold text-vf-navy">Recordings</h1><Button variant="ghost" onClick={() => void load()} disabled={loading}>Refresh</Button></div>
    {loading && <p role="status">Loading recordings…</p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {!loading && !error && items.length === 0 && <p className="text-slate-600">No recordings are available in your scope.</p>}
    <ul className="divide-y divide-slate-200">{items.map((item) => <li key={item.recording_id} className="flex flex-wrap justify-between gap-3 py-4"><Link href={`/recordings/${encodeURIComponent(item.recording_id)}`} className="font-bold text-vf-primary underline underline-offset-4">{item.recording_id}</Link><span className="tabular-nums text-slate-600">{item.duration_s.toFixed(1)} seconds</span></li>)}</ul>
    {cursor && <Button onClick={() => void load(cursor)} disabled={loading}>Load more recordings</Button>}
    {session?.roles.includes("Engineer") && <RecordingUpload onComplete={() => void load()} />}
  </div>;
}

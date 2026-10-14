import Link from "next/link";

export function V2WorkspaceUnavailable() {
  return <section className="section-card mx-auto max-w-xl space-y-4 p-6" aria-labelledby="v2-unavailable-title">
    <h1 id="v2-unavailable-title" className="text-xl font-bold">Recordings workspace is not enabled</h1>
    <p className="text-sm text-slate-600">This deployment uses Incidents. Recordings requires a separate V2 identity integration; signing in again will not enable it.</p>
    <Link href="/incidents" className="inline-block font-semibold text-vf-primary underline">Back to incidents</Link>
  </section>;
}

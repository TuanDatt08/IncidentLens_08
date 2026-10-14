"use client";

import Link from "next/link";
import { WorkspaceTheme } from "@/components/layout/workspace-theme";
import { LensMark } from "@/components/landing/landing-visuals";
import "@/app/auth-brand.css";

export function AuthLayout({ children, compact = false }: { children: React.ReactNode; compact?: boolean }) {
  return <div className="auth-layout auth-observatory" data-compact={compact}>
    <header className="auth-brandbar"><Link href="/" className="auth-brand"><LensMark /><span>Incident<span>Lens</span></span></Link><div className="auth-header-tools"><WorkspaceTheme /><Link href="/" className="auth-home-link">Back to home <span aria-hidden="true">↗</span></Link></div></header>
    <main className="auth-main">
      {!compact && <section className="auth-introduction" aria-labelledby="auth-introduction-title">
        <p className="auth-kicker">INCIDENT ANALYSIS WORKSPACE</p>
        <h2 id="auth-introduction-title">Every incident.<br />A clearer picture.</h2>
        <p className="auth-introduction-copy">Bring video, telemetry, and evidence together. Review the findings with your team before making the final call.</p>
        <ol className="auth-workflow">
          <li><span>01</span><div><strong>Capture the evidence</strong><p>Upload incident video and telemetry.</p></div></li>
          <li><span>02</span><div><strong>Examine every moment</strong><p>Trace findings back to their source.</p></div></li>
          <li><span>03</span><div><strong>Review with confidence</strong><p>Keep decisions and report versions together.</p></div></li>
        </ol>
      </section>}
      <div className="auth-panel">{children}</div>
    </main>
    <footer className="auth-footer">AI-assisted analysis · Human-led review</footer>
  </div>;
}

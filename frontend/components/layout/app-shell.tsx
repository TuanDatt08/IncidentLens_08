"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { AUTH_ENABLED, V2_WORKSPACE_ENABLED } from "@/lib/config";
import { ChevronDown, Lock } from "@/components/icons";
import { WorkspaceTheme } from "./workspace-theme";
import { LensMark } from "@/components/landing/landing-visuals";




export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user, can, signOut } = useAuth();

  const [error, setError] = useState("");
  const pathname = usePathname() ?? "/";
  const accountMenu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => { if (!accountMenu.current?.contains(event.target as Node)) accountMenu.current?.removeAttribute("open"); };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && accountMenu.current?.open) {
        accountMenu.current.removeAttribute("open");
        accountMenu.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => { document.removeEventListener("pointerdown", closeOutside); document.removeEventListener("keydown", closeOnEscape); };
  }, []);
  const closeMenu = () => accountMenu.current?.removeAttribute("open");
  const isCreate = pathname === "/incidents/new";
  const section = pathname.startsWith("/admin") ? "Users" : pathname.startsWith("/reports/") ? "Report review" : pathname.startsWith("/recordings/") ? "Recording analysis" : pathname.startsWith("/recordings") ? "Recordings" : isCreate ? "Upload incident" : pathname.endsWith("/processing") ? "Incident analysis" : pathname.startsWith("/incidents/") ? "Incident review" : "Incidents";
  return (
    <div className="workspace-shell workspace-header-shell min-h-screen" data-palette="custom">
      <a href="#workspace-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3 focus:text-vf-navy">Skip to content</a>
      <div className="workspace-body min-w-0">
        <header className="workspace-topbar flex min-h-16 items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Link href="/" className="header-brand" aria-label="IncidentLens home"><LensMark /><span>IncidentLens</span></Link>
            <span className="hidden text-xs text-[var(--workspace-muted)] sm:block">Workspace</span><span aria-hidden="true" className="hidden text-[var(--workspace-muted)] sm:block">/</span><span className="truncate text-sm font-bold text-[var(--workspace-ink)]">{section}</span>
          </div>
          <nav className="workspace-header-nav" aria-label="Workspace navigation">
            {can("incident:read") && <Link href="/incidents" aria-current={pathname.startsWith("/incidents") ? "page" : undefined}>Incidents</Link>}
            {can("incident:read") && V2_WORKSPACE_ENABLED && <Link href="/recordings" aria-current={pathname.startsWith("/recordings") ? "page" : undefined}>Recordings</Link>}
            {can("user:manage") && <Link href="/admin/users" aria-current={pathname.startsWith("/admin") ? "page" : undefined}>Users</Link>}
          </nav>
          <div className="workspace-topbar-tools">
          <WorkspaceTheme />
          {AUTH_ENABLED ? <details ref={accountMenu} className="group/account relative shrink-0">
            <summary role="button" aria-label="Account menu" className="flex cursor-pointer list-none items-center gap-2 rounded-xl p-1.5 transition hover:bg-[var(--workspace-primary-soft)] [&::-webkit-details-marker]:hidden">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--workspace-primary-soft)] text-[11px] font-extrabold uppercase text-[var(--workspace-primary)]">{user?.display_name.trim().slice(0, 2)}</span>
              <span className="hidden text-left md:block"><span className="block max-w-[140px] truncate text-xs font-extrabold text-[var(--workspace-ink)]">{user?.display_name}</span><span className="block max-w-[140px] truncate text-[10px] font-semibold capitalize text-[var(--workspace-muted)]">{user?.roles.join(", ")}</span></span>
              <span aria-hidden="true"><ChevronDown className="h-3.5 w-3.5 text-slate-400 transition group-open/account:rotate-180" /></span>
            </summary>
            <div className="absolute right-0 top-full z-40 mt-2 w-64 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-[var(--workspace-border)] bg-[var(--workspace-surface)] p-1.5 shadow-card">
              <div className="mb-1 border-b border-[var(--workspace-border)] px-3 py-3"><p className="truncate text-xs font-extrabold text-[var(--workspace-ink)]">{user?.display_name}</p><p className="mt-1 truncate text-[11px] text-[var(--workspace-muted)]">{user?.email}</p><p className="mt-1 text-[10px] capitalize text-[var(--workspace-muted)]">{user?.roles.join(", ")}</p></div>
              <Link href="/change-password" onClick={closeMenu} className="flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-xs font-bold text-[var(--workspace-ink)] hover:bg-[var(--workspace-primary-soft)]"><span aria-hidden="true"><Lock className="h-4 w-4" /></span> Change password</Link>
              <button onClick={() => { closeMenu(); void signOut().catch(cause => setError(cause instanceof Error ? cause.message : "Unable to sign out. Try again.")); }} className="mt-1 flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-xs font-bold text-[var(--workspace-muted)] transition hover:bg-red-50 hover:text-red-600"><svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M10 4H5v16h5m4-13 5 5-5 5m-5-5h10" strokeLinecap="round" strokeLinejoin="round" /></svg>Sign out</button>
            </div>
          </details> : null}</div>
        </header>
        {error && <p role="alert" className="auth-error mx-5 mt-4">{error}</p>}
        <main id="workspace-content" tabIndex={-1} className="workspace-main w-full">{children}</main>
      </div>
    </div>
  );
}

import Link from "next/link";
import { Film, Plus, UserCircle } from "@/components/icons";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-[76px] max-w-[1440px] items-center justify-between px-6 lg:px-10">
          <Link href="/incidents" className="group flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-vf-navy text-white shadow-soft transition group-hover:bg-vf-primary">
              <Film className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-[17px] font-extrabold leading-tight tracking-[-0.02em] text-vf-navy">IncidentLens</span>
              <span className="mt-0.5 block text-[10px] font-bold uppercase tracking-[0.11em] text-slate-400">AI-assisted ADAS analysis</span>
            </span>
          </Link>

          <nav className="flex items-center gap-2 sm:gap-5">
            <Link href="/incidents" className="hidden text-sm font-bold text-slate-600 transition hover:text-vf-primary sm:block">Incidents</Link>
            <Link href="/incidents/new" className="inline-flex items-center gap-2 rounded-xl bg-vf-primary px-4 py-2.5 text-sm font-extrabold text-white shadow-[0_7px_15px_rgba(20,100,244,0.18)] transition hover:bg-blue-700">
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Create Incident</span>
              <span className="sm:hidden">Create</span>
            </Link>
            <span className="ml-1 hidden h-8 w-px bg-slate-200 md:block" />
            <div className="hidden items-center gap-2 text-right md:flex">
              <div>
                <p className="text-xs font-extrabold text-vf-navy">ADAS Engineering</p>
                <p className="text-[10px] font-semibold text-slate-400">Reviewer workspace</p>
              </div>
              <UserCircle className="h-9 w-9 text-slate-400" />
            </div>
          </nav>
        </div>
      </header>
      <main className="mx-auto min-h-[calc(100vh-76px)] max-w-[1440px] px-6 py-8 lg:px-10 lg:py-10">{children}</main>
    </div>
  );
}
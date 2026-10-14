"use client";

import { useEffect, useRef } from "react";
import { X } from "@/components/icons";
import { useAuth } from "./auth-provider";

export function AccountDialog({ title, description, busy, onClose, children }: { title: string; description: string; busy: boolean; onClose: () => void; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const { status } = useAuth();
  useEffect(() => {
    const dialog = ref.current;
    if (!opener.current) opener.current = document.activeElement as HTMLElement | null;
    // Native dialogs occupy the top layer: close them while reauthentication
    // is shown, then restore the same form when the session returns.
    if (status === "authenticated") dialog?.showModal();
    else dialog?.close();
    return () => {
      dialog?.close();
      if (opener.current?.isConnected) opener.current.focus({ preventScroll: true });
    };
  }, [status]);
  return <dialog ref={ref} aria-labelledby="account-dialog-title" aria-describedby="account-dialog-description" onCancel={event => { event.preventDefault(); if (!busy) onClose(); }} className="m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-2xl border border-slate-100 bg-white p-0 text-vf-text shadow-[0_24px_80px_rgba(13,21,40,0.2)] backdrop:bg-vf-navy/45 backdrop:backdrop-blur-sm">
    <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5 sm:px-7">
      <div><p className="eyebrow">Workspace access</p><h2 id="account-dialog-title" className="mt-2 text-xl font-extrabold tracking-[-0.025em] text-vf-navy">{title}</h2><p id="account-dialog-description" className="mt-2 text-xs leading-5 text-slate-500">{description}</p></div>
      <button type="button" aria-label="Close dialog" disabled={busy} onClick={onClose} className="icon-button h-8 w-8 shrink-0"><X className="h-4 w-4" /></button>
    </header>
    {children}
  </dialog>;
}

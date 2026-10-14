"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { changePassword } from "@/services/auth.service";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/auth-layout";
import { PasswordField } from "@/components/auth/password-field";
import { ArrowLeft, ArrowRight, Lock } from "@/components/icons";
import { Button } from "@/components/ui/button";

export default function ChangePasswordPage() {
  const { clear, signOut, status } = useAuth();
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await changePassword(current, password); clear(); router.replace("/login"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Password change failed."); }
    finally { setBusy(false); setCurrent(""); setPassword(""); }
  }
  if (status !== "password-change-required" && status !== "authenticated") return <AuthLayout compact><p role="status" className="text-center text-sm font-semibold text-slate-500">Opening sign in…</p></AuthLayout>;
  return <AuthLayout compact><form onSubmit={submit} aria-busy={busy}>
    <span className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-vf-primary"><Lock className="h-5 w-5" /></span>
    <p className="eyebrow">{status === "password-change-required" ? "One last step" : "Account settings"}</p>
    <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em] text-vf-navy">Change password</h1>
    <p className="mt-3 text-sm leading-6 text-slate-500">{status === "password-change-required" ? "Replace your temporary password to enter the workspace." : "Choose a new password for your workspace account."}</p>
    <div className="mt-8 space-y-5">
      <PasswordField label="Current password" required disabled={busy} autoComplete="current-password" placeholder="Enter current password" value={current} onChange={event => setCurrent(event.target.value)} />
      <PasswordField label="New password" required disabled={busy} minLength={6} maxLength={128} autoComplete="new-password" placeholder="Choose a new password" hint="Use at least 6 characters." value={password} onChange={event => setPassword(event.target.value)} />
      {error && <p role="alert" className="auth-error">{error}</p>}
      <Button type="submit" className="!min-h-12 w-full" disabled={busy}>{busy ? "Updating password…" : "Change password"}{!busy && <ArrowRight className="h-4 w-4" />}</Button>
    </div>
    <p className="mt-4 text-center text-xs leading-5 text-slate-400">You&apos;ll sign in again with your new password.</p>
    <div className="mt-6 flex items-center justify-center gap-4 border-t border-slate-100 pt-5">
      {status === "authenticated" && <Link href="/incidents" className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 transition hover:text-vf-primary"><ArrowLeft className="h-3.5 w-3.5" /> Back to workspace</Link>}
      <button type="button" disabled={busy} className="text-xs font-bold text-slate-500 transition hover:text-vf-primary disabled:opacity-50" onClick={() => void signOut().catch(cause => setError(cause.message))}>Sign out</button>
    </div>
  </form></AuthLayout>;
}

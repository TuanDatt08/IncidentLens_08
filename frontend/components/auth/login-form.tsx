"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { safeReturnUrl } from "@/lib/return-url";
import { ArrowRight, Lock } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { PasswordField } from "./password-field";

export function LoginForm({ reauthenticate = false }: { reauthenticate?: boolean }) {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const user = await signIn(email, password);
      setPassword("");
      if (user.must_change_password) router.replace("/change-password");
      else if (!reauthenticate) router.replace(safeReturnUrl(new URLSearchParams(window.location.search).get("returnTo")));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Sign in failed."); }
    finally { setBusy(false); setPassword(""); }
  }
  return <form onSubmit={submit} className="w-full auth-login-form" aria-busy={busy}>
    <span className="auth-login-icon"><Lock className="h-5 w-5" /></span>
    <p className="eyebrow">{reauthenticate ? "Continue your session" : "Welcome back"}</p>
    <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.04em] text-vf-navy">Sign in</h1>
    <p className="mt-3 text-sm leading-6 text-slate-500">{reauthenticate ? "Use your workspace account to pick up where you left off." : "Access your incidents, evidence, and team reviews."}</p>
    <div className="mt-8 space-y-5">
      <div><label htmlFor="login-email" className="field-label">Email</label><input id="login-email" className="auth-input" type="email" autoComplete="username" placeholder="you@company.com" required disabled={busy} value={email} onChange={event => setEmail(event.target.value)} /></div>
      <PasswordField label="Password" autoComplete="current-password" placeholder="Enter your password" maxLength={128} required disabled={busy} value={password} onChange={event => setPassword(event.target.value)} />
      {error && <p role="alert" className="auth-error">{error}</p>}
      <Button type="submit" className="!min-h-12 w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}{!busy && <ArrowRight className="h-4 w-4" />}</Button>
    </div>
    <p className="mt-7 border-t border-slate-100 pt-5 text-center text-xs leading-6 text-slate-400">Need access? <span className="font-bold text-slate-500">Contact your workspace administrator.</span></p>
  </form>;
}

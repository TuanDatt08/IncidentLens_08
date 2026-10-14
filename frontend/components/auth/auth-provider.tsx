"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ApiError, setSessionTransport } from "@/lib/api-client";
import { getSession, login, logout } from "@/services/auth.service";
import { hasPermission, type AuthSession, type Permission, type User } from "@/types/auth";
import { AppShell } from "@/components/layout/app-shell";
import { LoginForm } from "./login-form";
import { AuthLayout } from "./auth-layout";
import { Lock } from "@/components/icons";
import Link from "next/link";
import { AUTH_ENABLED } from "@/lib/config";

type Status = "loading" | "authenticated" | "anonymous" | "password-change-required";
type AuthState = { status: Status; user?: User; can: (permission: Permission) => boolean; signIn: (email: string, password: string) => Promise<User>; signOut: () => Promise<void>; clear: () => void };
const AuthContext = createContext<AuthState | undefined>(undefined);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // The public product page never mounts workspace session or permission logic.
  if (pathname === "/") return <>{children}</>;
  return AUTH_ENABLED ? <AuthenticatedProvider>{children}</AuthenticatedProvider> : <InternalWorkspaceProvider>{children}</InternalWorkspaceProvider>;
}

const internalWorkspace: AuthState = {
  status: "authenticated",
  can: permission => permission !== "user:manage",
  signIn: async () => { throw new Error("Authentication is not enabled in this workspace."); },
  signOut: async () => { throw new Error("Authentication is not enabled in this workspace."); },
  clear: () => {},
};

function InternalWorkspaceProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const authPage = pathname === "/login" || pathname === "/change-password" || pathname === "/admin" || pathname.startsWith("/admin/");
  return <AuthContext.Provider value={internalWorkspace}><AppShell>{authPage ? <section className="section-card mx-auto max-w-xl space-y-4 p-6">
    <h1 className="text-xl font-bold">Authentication is not enabled</h1>
    <p className="text-sm text-slate-600">Account features are unavailable in this internal workspace.</p>
    <Link href="/incidents" className="inline-block font-semibold text-vf-primary underline">Back to incidents</Link>
  </section> : children}</AppShell></AuthContext.Provider>;
}

function AuthenticatedProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User>();
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const lastUser = useRef<string>();
  const router = useRouter();
  const pathname = usePathname();
  const accept = useCallback((session: AuthSession) => {
    if (lastUser.current && lastUser.current !== session.user.id) setEpoch(value => value + 1);
    lastUser.current = session.user.id;
    setSessionTransport(session.csrf_token);
    setUser(session.user);
    setError("");
    setExpired(false);
    setStatus(session.user.must_change_password ? "password-change-required" : "authenticated");
  }, []);
  const clear = useCallback(() => {
    setSessionTransport();
    setUser(undefined);
    setStatus("anonymous");
    setError("");
    setExpired(false);
    lastUser.current = undefined;
    setEpoch(value => value + 1);
    // Only clear this application's transient job identifiers.
    for (const key of Object.keys(window.sessionStorage)) if ((key.startsWith("analysis-job:") || key.startsWith("incidentlens:report-draft:"))) window.sessionStorage.removeItem(key);
  }, []);
  useEffect(() => {
    let active = true;
    const expire = () => {
      setSessionTransport();
      setStatus("anonymous");
      setExpired(Boolean(lastUser.current));
      document.querySelectorAll("video").forEach(video => video.pause());
    };
    window.addEventListener("auth:expired", expire);
    getSession().then(session => { if (active) accept(session); }).catch(reason => {
      if (!active) return;
      setStatus("anonymous");
      if (!(reason instanceof ApiError && reason.status === 401)) setError("Unable to check your session. Reload to try again.");
    });
    return () => { active = false; window.removeEventListener("auth:expired", expire); };
  }, [accept]);
  useEffect(() => {
    if (status === "loading" || expired || error) return;
    if (status === "anonymous" && pathname !== "/login") router.replace(`/login?returnTo=${encodeURIComponent(pathname)}`);
    if (status === "password-change-required" && pathname !== "/change-password") router.replace("/change-password");
  }, [status, pathname, router, expired, error]);
  const signIn = async (email: string, password: string) => {
    const session = await login(email, password);
    accept(session);
    return session.user;
  };
  const signOut = async () => {
    try { await logout(); }
    catch (reason) { if (!(reason instanceof ApiError && reason.status === 401)) throw reason; }
    clear();
    router.replace("/login");
    router.refresh();
  };
  const value: AuthState = { status, user, can: permission => status === "authenticated" && hasPermission(user, permission), signIn, signOut, clear };
  const publicPage = pathname === "/login" || pathname === "/change-password";
  const allowed = expired || (!(pathname.startsWith("/admin") && !hasPermission(user, "user:manage")) && !(pathname === "/incidents/new" && !hasPermission(user, "incident:create")));
  return <AuthContext.Provider value={value}>
    {status === "loading" ? <AuthLayout compact><p role="status" className="flex items-center justify-center gap-3 py-12 text-sm font-semibold text-slate-500"><span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-100 border-t-vf-primary" /> Checking session…</p></AuthLayout> : error ? <AuthLayout compact><p role="alert" className="auth-error">{error}</p><button onClick={() => window.location.reload()} className="mt-5 text-sm font-extrabold text-vf-primary">Try again</button></AuthLayout> : publicPage ? children : status === "authenticated" || expired ? <>
      <div hidden={expired} key={epoch}><AppShell>{allowed ? children : <div className="section-card mx-auto mt-12 max-w-lg p-8 text-center"><Lock className="mx-auto h-8 w-8 text-slate-400" /><h1 className="mt-4 text-xl font-extrabold text-vf-navy">Access restricted</h1><p className="mt-3 text-sm leading-6 text-slate-500">You do not have permission to view this page.</p><p className="mt-1 text-xs leading-5 text-slate-400">Contact your administrator if you need access.</p></div>}</AppShell></div>
      {expired && <AuthLayout compact><p role="alert" className="mb-6 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs font-semibold leading-6 text-amber-800">Your session ended. Sign in again to continue. Your unsaved draft is kept in memory; saving still requires your action.</p><LoginForm reauthenticate /></AuthLayout>}
    </> : <AuthLayout compact><p role="status" className="text-center text-sm font-semibold text-slate-500">Opening sign in…</p></AuthLayout>}
  </AuthContext.Provider>;
}

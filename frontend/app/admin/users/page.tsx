"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { createUser, listUsers, resetPassword, updateUser } from "@/services/user.service";
import type { Role, User } from "@/types/auth";
import { Lock, Plus, UserCircle } from "@/components/icons";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { AccountDialog } from "@/components/auth/account-dialog";
import { PasswordField } from "@/components/auth/password-field";

const roleDetails: Record<Role, { description: string; color: string }> = {
  engineer: { description: "Upload incidents, edit reports, and submit for review.", color: "border-blue-100 bg-blue-50 text-blue-700" },
  reviewer: { description: "Review evidence and approve or reject reports.", color: "border-violet-100 bg-violet-50 text-violet-700" },
  admin: { description: "Manage accounts and workspace access.", color: "border-slate-200 bg-slate-100 text-slate-600" },
};

export default function UsersPage() {
  const { can, user: currentUser, status } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [editing, setEditing] = useState<User | "create">();
  const [resetting, setResetting] = useState<User>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    listUsers(offset).then(data => { if (active) { setUsers(data.items); setTotal(data.total); } }).catch(cause => { if (active) setError(cause.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [offset, revision]);
  async function toggle(user: User) {
    setError(""); setBusy(true);
    try { await updateUser(user.id, { is_active: !user.is_active }); setRevision(value => value + 1); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Account update failed."); }
    finally { setBusy(false); }
  }
  // AuthProvider hides this subtree during reauthentication. Permission
  // availability drops while the session expires; keep the form's draft mounted.
  if (status === "authenticated" && currentUser && !can("user:manage")) return <p>You do not have permission to view this page.</p>;
  return <section className="mx-auto max-w-[1200px] space-y-7 py-3 sm:py-5">
    <PageHeader title="Users" description="Manage team accounts, roles and workspace access." action={<Button onClick={() => { setEditing("create"); setError(""); }}><Plus className="h-4 w-4" /> Create user</Button>} />
    {error && <div className="auth-error flex flex-wrap items-center justify-between gap-3"><p role="alert">{error}</p><Button variant="ghost" disabled={loading || busy} onClick={() => setRevision(value => value + 1)}>Retry</Button></div>}
    <div className="section-card overflow-hidden">
      <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-5 sm:px-7"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-vf-primary"><UserCircle className="h-6 w-6" /></span><div><h2 className="text-sm font-extrabold text-vf-navy">Team directory <span className="ml-2 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">{total}</span></h2><p className="mt-1 text-xs text-slate-400">Control who can contribute and review.</p></div></div>
      {loading && !users.length && !error ? <div role="status" className="space-y-4 p-7"><span className="sr-only">Loading users…</span>{[1, 2, 3].map(index => <div key={index} className="h-12 animate-pulse rounded-xl bg-slate-100" />)}</div> : !users.length && !error ? <div className="p-12 text-center"><UserCircle className="mx-auto h-10 w-10 text-slate-300" /><p className="mt-4 font-extrabold text-vf-navy">No users to display</p><p className="mt-2 text-sm text-slate-400">Create a user to give someone workspace access.</p></div> :
      <div className="overflow-x-auto"><table className="block w-full text-left lg:table"><thead className="hidden border-b border-slate-100 bg-slate-50/70 lg:table-header-group"><tr>{["Team member", "Roles", "Status", "Actions"].map(label => <th key={label} className="px-6 py-3 text-[10px] font-extrabold uppercase tracking-[0.12em] text-slate-400 first:pl-7 last:text-right">{label}</th>)}</tr></thead><tbody className="block divide-y divide-slate-100 lg:table-row-group">{users.map(user => <tr key={user.id} className="grid grid-cols-2 gap-4 p-5 transition hover:bg-slate-50/50 lg:table-row lg:p-0">
        <td className="col-span-2 block lg:table-cell lg:py-5 lg:pl-7 lg:pr-6"><div className="flex items-center gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-xs font-extrabold uppercase text-vf-primary">{user.display_name.trim().slice(0, 2)}</span><div className="min-w-0"><p className="break-words text-sm font-extrabold text-vf-navy">{user.display_name}{user.id === currentUser?.id && <span className="ml-2 text-[10px] font-bold text-slate-400">You</span>}</p><p className="mt-1 break-all text-xs text-slate-400">{user.email}</p></div></div></td>
        <td className="block lg:table-cell lg:px-6 lg:py-5"><span className="mb-2 block text-[10px] font-extrabold uppercase tracking-wider text-slate-400 lg:hidden">Roles</span><div className="flex flex-wrap gap-1.5">{user.roles.map(role => <span key={role} className={`rounded-md border px-2 py-1 text-[10px] font-extrabold capitalize ${roleDetails[role].color}`}>{role}</span>)}</div></td>
        <td className="block lg:table-cell lg:px-6 lg:py-5"><span className="mb-2 block text-[10px] font-extrabold uppercase tracking-wider text-slate-400 lg:hidden">Status</span><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-extrabold ${user.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}><span className={`h-1.5 w-1.5 rounded-full ${user.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />{user.is_active ? "Active" : "Locked"}</span>{user.must_change_password && <p className="mt-2 max-w-[155px] text-[10px] font-semibold leading-4 text-amber-700">Password change required</p>}</td>
        <td className="col-span-2 block border-t border-slate-100 pt-3 lg:table-cell lg:border-0 lg:px-6 lg:py-5"><div className="flex flex-wrap items-center gap-1 lg:justify-end"><button className="rounded-lg px-2.5 py-2 text-xs font-extrabold text-vf-primary transition hover:bg-blue-50 disabled:opacity-40" disabled={busy} onClick={() => { setEditing(user); setError(""); }}>Edit user</button><button className={`rounded-lg px-2.5 py-2 text-xs font-bold transition disabled:opacity-40 ${user.is_active ? "text-slate-500 hover:bg-red-50 hover:text-red-600" : "text-emerald-700 hover:bg-emerald-50"}`} disabled={busy} onClick={() => void toggle(user)}>{user.is_active ? "Lock" : "Unlock"}</button><button className="rounded-lg px-2.5 py-2 text-xs font-bold text-slate-500 transition hover:bg-slate-100 hover:text-vf-navy disabled:opacity-40" disabled={busy} onClick={() => { setResetting(user); setError(""); }}>Reset password</button></div></td>
      </tr>)}</tbody></table></div>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-4 sm:px-7"><p className="text-xs font-semibold text-slate-400">Showing {total === 0 ? 0 : offset + 1}–{Math.min(offset + users.length, total)} of {total} users</p><div className="flex gap-1"><button disabled={loading || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))} className="rounded-lg px-3 py-2 text-xs font-bold text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-35">Previous</button><button disabled={loading || offset + 20 >= total} onClick={() => setOffset(value => value + 20)} className="rounded-lg px-3 py-2 text-xs font-bold text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-35">Next</button></div></div>
    </div>
    <p className="flex items-start gap-2.5 px-1 text-xs leading-6 text-slate-400"><Lock className="mt-1 h-3.5 w-3.5 shrink-0" />Role changes, account locks, and password resets require the affected user to sign in again.</p>
    {editing && <UserForm key={editing === "create" ? "create" : editing.id} user={editing === "create" ? undefined : editing} onClose={() => setEditing(undefined)} onDone={() => { setEditing(undefined); setRevision(value => value + 1); }} />}
    {resetting && <ResetForm user={resetting} onClose={() => setResetting(undefined)} onDone={() => { setResetting(undefined); setRevision(value => value + 1); }} />}
  </section>;
}

function UserForm({ user, onClose, onDone }: { user?: User; onClose: () => void; onDone: () => void }) {
  const [email, setEmail] = useState(user?.email ?? "");
  const [name, setName] = useState(user?.display_name ?? "");
  const [roles, setRoles] = useState<Role[]>(user?.roles ?? ["engineer"]);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (user) await updateUser(user.id, { display_name: name, roles });
      else await createUser({ email, display_name: name, roles, temporary_password: password });
      setPassword(""); onDone();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Account update failed."); }
    finally { setBusy(false); setPassword(""); }
  }
  function close() { setPassword(""); onClose(); }
  return <AccountDialog title={user ? "Edit user" : "Create user"} description={user ? "Update this team member’s name and permissions." : "Give a team member access to the workspace."} busy={busy} onClose={close}><form onSubmit={submit} className="space-y-5 p-6 sm:p-7" aria-busy={busy}>
    <div><label htmlFor="user-email" className="field-label">Email</label><input id="user-email" type="email" required disabled={Boolean(user) || busy} placeholder="teammate@company.com" autoComplete="off" className="auth-input" value={email} onChange={event => setEmail(event.target.value)} /></div>
    <div><label htmlFor="user-name" className="field-label">Display name</label><input id="user-name" required disabled={busy} maxLength={255} placeholder="Full name" className="auth-input" value={name} onChange={event => setName(event.target.value)} /></div>
    <fieldset disabled={busy}><legend className="field-label">Roles</legend><div className="space-y-2">{(Object.keys(roleDetails) as Role[]).map(role => <label key={role} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${roles.includes(role) ? "border-blue-200 bg-blue-50/50" : "border-slate-200 hover:bg-slate-50"}`}><input type="checkbox" aria-label={role} className="mt-0.5 h-4 w-4 shrink-0 accent-vf-primary" checked={roles.includes(role)} onChange={event => setRoles(current => event.target.checked ? [...current, role] : current.filter(value => value !== role))} /><span><span className="block text-xs font-extrabold capitalize text-vf-navy">{role}</span><span className="mt-1 block text-[11px] leading-5 text-slate-500">{roleDetails[role].description}</span></span></label>)}</div><p className="mt-2 text-[11px] leading-5 text-slate-400">Select at least one role. Multiple roles are supported.</p></fieldset>
    {!user && <PasswordField label="Temporary password" required disabled={busy} minLength={6} maxLength={128} autoComplete="new-password" placeholder="At least 6 characters" hint="The user will choose a new password when they first sign in." value={password} onChange={event => setPassword(event.target.value)} />}
    {error && <p role="alert" className="auth-error">{error}</p>}
    <div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><Button variant="ghost" type="button" disabled={busy} onClick={close}>Cancel</Button><Button type="submit" disabled={busy || !roles.length}>{busy ? "Saving…" : "Save user"}</Button></div>
  </form></AccountDialog>;
}

function ResetForm({ user, onClose, onDone }: { user: User; onClose: () => void; onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await resetPassword(user.id, password); setPassword(""); onDone(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Password reset failed."); }
    finally { setBusy(false); setPassword(""); }
  }
  function close() { setPassword(""); onClose(); }
  return <AccountDialog title="Reset password" description="Set a temporary password for this team member." busy={busy} onClose={close}><form onSubmit={submit} className="space-y-5 p-6 sm:p-7" aria-busy={busy}>
    <div className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4"><UserCircle className="h-9 w-9 shrink-0 text-slate-400" /><div className="min-w-0"><p className="text-sm font-extrabold text-vf-navy">{user.display_name}</p><p className="mt-1 break-all text-xs text-slate-500">{user.email}</p></div></div>
    <PasswordField label="Temporary password" required disabled={busy} minLength={6} maxLength={128} autoComplete="new-password" placeholder="At least 6 characters" value={password} onChange={event => setPassword(event.target.value)} />
    <p className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-800">This signs the user out of all sessions. They&apos;ll need to change this password at their next sign-in.</p>
    {error && <p role="alert" className="auth-error">{error}</p>}
    <div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><Button type="button" variant="ghost" disabled={busy} onClick={close}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? "Resetting…" : "Reset password"}</Button></div>
  </form></AccountDialog>;
}

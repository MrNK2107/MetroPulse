"use client";

import { useState } from "react";
import type { CloudApi } from "@/lib/cloud/useCloud";
import type { Role } from "@/lib/cloud/workspaces";

const btn = "border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal disabled:opacity-40";
const field = "border border-ink bg-paper px-2 py-1 text-sm";

/** Sign-in, workspace and sync controls for the optional cloud. Renders nothing when no cloud is configured. */
export function AccountMenu({ cloud }: { cloud: CloudApi }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [creating, setCreating] = useState(false);
  const [wsName, setWsName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Exclude<Role, "owner">>("editor");
  if (!cloud.configured) return null;

  if (cloud.user) {
    const isOwner = cloud.active !== null && cloud.role === "owner";
    return (
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="hidden font-mono text-[11px] text-ink-soft sm:inline" title="Signed in">
          {cloud.user.email}
        </span>
        <label className="flex items-center gap-1">
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink-soft">Workspace</span>
          <select value={cloud.active ?? ""} onChange={(e) => cloud.setActive(e.target.value || null)} className={field}>
            <option value="">Personal</option>
            {cloud.workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        {cloud.active && cloud.role && (
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">Role: {cloud.role}</span>
        )}
        {creating ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void cloud.createWorkspace(wsName);
              setWsName("");
              setCreating(false);
            }}
            className="flex items-center gap-1"
          >
            <label>
              <span className="sr-only">Workspace name</span>
              <input value={wsName} onChange={(e) => setWsName(e.target.value)} placeholder="Team name" className={field} required />
            </label>
            <button type="submit" className={btn}>
              Create
            </button>
          </form>
        ) : (
          <button type="button" onClick={() => setCreating(true)} className={btn}>
            New workspace
          </button>
        )}
        {isOwner && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (inviteEmail.trim()) void cloud.invite(inviteEmail, inviteRole);
              setInviteEmail("");
            }}
            className="flex items-center gap-1"
          >
            <label>
              <span className="sr-only">Invite email</span>
              <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="colleague@authority.gov.in" className={field} required />
            </label>
            <label>
              <span className="sr-only">Invite role</span>
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as Exclude<Role, "owner">)} className={field}>
                <option value="editor">Editor</option>
                <option value="viewer">Viewer</option>
              </select>
            </label>
            <button type="submit" className={btn}>
              Invite
            </button>
          </form>
        )}
        <button type="button" onClick={() => void cloud.sync()} disabled={cloud.busy} className={btn}>
          {cloud.busy ? "Syncing…" : "Sync now"}
        </button>
        <button type="button" onClick={() => void cloud.signOut()} className={btn}>
          Sign out
        </button>
        {cloud.notice && (
          <span role="status" className="basis-full font-mono text-[11px] text-ink-faint">
            {cloud.notice}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className={btn}>
        Sign in
      </button>
      {open && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (email.trim()) void cloud.signIn(email.trim());
          }}
          className="absolute right-0 z-40 mt-1 w-72 border-2 border-ink bg-paper p-3 shadow-[6px_6px_0_0_#16130F]"
        >
          <p className="font-display text-base font-semibold">Workspace sign-in</p>
          <p className="mt-1 text-xs text-ink-soft">
            A magic link by email. Signed in, your saved lines sync to your workspace and follow you across devices; team
            workspaces share them with colleagues by role.
          </p>
          <label className="mt-2 block text-xs">
            <span className="font-mono text-[10px] uppercase tracking-widest text-ink-soft">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-0.5 w-full border border-ink bg-paper px-2 py-1 text-sm"
              placeholder="you@authority.gov.in"
            />
          </label>
          <button type="submit" disabled={cloud.busy} className={`${btn} mt-2 w-full bg-ink text-paper hover:bg-supply`}>
            Send magic link
          </button>
          {cloud.notice && (
            <p role="status" className="mt-2 text-xs text-ink-soft">
              {cloud.notice}
            </p>
          )}
        </form>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import type { CloudApi } from "@/lib/cloud/useCloud";

const btn = "border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal disabled:opacity-40";

/** Sign-in and sync controls for the optional cloud workspace. Renders nothing when no cloud is configured. */
export function AccountMenu({ cloud }: { cloud: CloudApi }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  if (!cloud.configured) return null;

  if (cloud.user) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="hidden font-mono text-[11px] text-ink-soft sm:inline" title="Signed in">
          {cloud.user.email}
        </span>
        <button type="button" onClick={() => void cloud.sync()} disabled={cloud.busy} className={btn}>
          {cloud.busy ? "Syncing…" : "Sync now"}
        </button>
        <button type="button" onClick={() => void cloud.signOut()} className={btn}>
          Sign out
        </button>
        {cloud.notice && (
          <span role="status" className="hidden font-mono text-[11px] text-ink-faint md:inline">
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
            A magic link by email. Signed in, your saved lines sync to your workspace and follow you across devices.
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

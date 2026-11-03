"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Scenario } from "@/lib/pulse/scenario";
import { getSupabase, isCloudConfigured, supabaseStore } from "./supabase";
import { syncScenarios, toRow } from "./scenarioSync";

export interface CloudUser {
  id: string;
  email: string;
}

export interface CloudApi {
  configured: boolean;
  user: CloudUser | null;
  busy: boolean;
  notice: string;
  signIn(email: string): Promise<void>;
  signOut(): Promise<void>;
  sync(): Promise<void>;
  /** Mirror one saved line to the cloud when signed in; a no-op otherwise. */
  pushLine(s: Scenario): Promise<void>;
  removeLine(id: string): Promise<void>;
}

/** Optional cloud workspace: Supabase magic-link sign-in and two-way scenario sync for one city. */
export function useCloud(cityId: string, onSynced?: (r: { pulled: number; pushed: number }) => void): CloudApi {
  const configured = isCloudConfigured();
  const [user, setUser] = useState<CloudUser | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const synced = useRef<string>("");
  const onSyncedRef = useRef(onSynced);
  onSyncedRef.current = onSynced;

  const sync = useCallback(
    async (u: CloudUser | null = user) => {
      const sb = getSupabase();
      if (!sb || !u) return;
      setBusy(true);
      try {
        const r = await syncScenarios(supabaseStore(sb), u.id, cityId);
        setNotice(r.pulled || r.pushed ? `Synced: ${r.pulled} pulled, ${r.pushed} pushed` : "Library in sync");
        onSyncedRef.current?.(r);
      } catch (e) {
        setNotice(e instanceof Error ? `Sync failed: ${e.message}` : "Sync failed");
      } finally {
        setBusy(false);
      }
    },
    [cityId, user]
  );

  useEffect(() => {
    const sb = getSupabase();
    if (!sb) return;
    let active = true;
    const apply = (session: { user: { id: string; email?: string | null } } | null) => {
      if (!active) return;
      const u = session?.user ? { id: session.user.id, email: session.user.email ?? "" } : null;
      setUser(u);
      const key = u ? `${u.id}:${cityId}` : "";
      if (u && synced.current !== key) {
        synced.current = key;
        void sync(u);
      }
      if (!u) synced.current = "";
    };
    sb.auth.getSession().then(({ data }) => apply(data.session));
    const { data } = sb.auth.onAuthStateChange((_event, session) => apply(session));
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
    // sync changes identity with `user`; the effect only needs the city and the client.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityId]);

  const signIn = useCallback(async (email: string) => {
    const sb = getSupabase();
    if (!sb) return;
    setBusy(true);
    const redirect = typeof window !== "undefined" ? window.location.href : undefined;
    const { error } = await sb.auth.signInWithOtp({ email, options: { emailRedirectTo: redirect } });
    setBusy(false);
    setNotice(error ? `Could not send the link: ${error.message}` : "Check your inbox for the sign-in link");
  }, []);

  const signOut = useCallback(async () => {
    const sb = getSupabase();
    if (!sb) return;
    await sb.auth.signOut();
    setUser(null);
    setNotice("Signed out; your lines stay on this device");
  }, []);

  const pushLine = useCallback(
    async (s: Scenario) => {
      const sb = getSupabase();
      if (!sb || !user) return;
      try {
        await supabaseStore(sb).upsert([toRow(s, user.id)]);
      } catch (e) {
        setNotice(e instanceof Error ? `Cloud save failed: ${e.message}` : "Cloud save failed");
      }
    },
    [user]
  );

  const removeLine = useCallback(
    async (id: string) => {
      const sb = getSupabase();
      if (!sb || !user) return;
      try {
        await supabaseStore(sb).remove(id);
      } catch {
        /* the local delete already happened; the next sync re-pulls if the cloud still has it */
      }
    },
    [user]
  );

  return { configured, user, busy, notice, signIn, signOut, sync: () => sync(), pushLine, removeLine };
}

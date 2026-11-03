"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Scenario } from "@/lib/pulse/scenario";
import { getSupabase, isCloudConfigured, supabaseStore } from "./supabase";
import { syncScenarios, toRow } from "./scenarioSync";
import { canEdit, Role, supabaseWorkspaces, Workspace, WorkspaceStore } from "./workspaces";

export interface CloudUser {
  id: string;
  email: string;
}

export interface CloudApi {
  configured: boolean;
  user: CloudUser | null;
  busy: boolean;
  notice: string;
  /** Team workspaces the user belongs to; `active` is null for the personal library. */
  workspaces: Workspace[];
  active: string | null;
  role: Role | null;
  canEdit: boolean;
  setActive(id: string | null): void;
  createWorkspace(name: string): Promise<void>;
  invite(email: string, role: Exclude<Role, "owner">): Promise<void>;
  signIn(email: string): Promise<void>;
  signOut(): Promise<void>;
  sync(): Promise<void>;
  /** Mirror one saved line to the active scope when signed in and allowed; a no-op otherwise. */
  pushLine(s: Scenario): Promise<void>;
  removeLine(id: string): Promise<void>;
}

/** Optional cloud workspace: Supabase magic-link sign-in, team workspaces, and two-way scenario sync for one city. */
export function useCloud(cityId: string, onSynced?: (r: { pulled: number; pushed: number }) => void): CloudApi {
  const configured = isCloudConfigured();
  const [user, setUser] = useState<CloudUser | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [active, setActiveState] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const onSyncedRef = useRef(onSynced);
  onSyncedRef.current = onSynced;
  const wsStore = useRef<WorkspaceStore | null>(null);

  const stores = useCallback((u: CloudUser | null) => {
    const sb = getSupabase();
    if (!sb || !u) return null;
    if (!wsStore.current) wsStore.current = supabaseWorkspaces(sb, u);
    return { lines: supabaseStore(sb), ws: wsStore.current };
  }, []);

  const sync = useCallback(
    async (u: CloudUser | null = user, scope: string | null = active) => {
      const s = stores(u);
      if (!s || !u) return;
      setBusy(true);
      try {
        const r = await syncScenarios(s.lines, u.id, cityId, scope);
        setNotice(r.pulled || r.pushed ? `Synced: ${r.pulled} pulled, ${r.pushed} pushed` : "Library in sync");
        onSyncedRef.current?.(r);
      } catch (e) {
        setNotice(e instanceof Error ? `Sync failed: ${e.message}` : "Sync failed");
      } finally {
        setBusy(false);
      }
    },
    [cityId, user, active, stores]
  );

  const loadWorkspaces = useCallback(
    async (u: CloudUser) => {
      const s = stores(u);
      if (!s) return;
      try {
        setWorkspaces(await s.ws.list());
      } catch (e) {
        setNotice(e instanceof Error ? `Could not load workspaces: ${e.message}` : "Could not load workspaces");
      }
    },
    [stores]
  );

  useEffect(() => {
    const sb = getSupabase();
    if (!sb) return;
    let live = true;
    let syncedFor = "";
    const apply = (session: { user: { id: string; email?: string | null } } | null) => {
      if (!live) return;
      const u = session?.user ? { id: session.user.id, email: session.user.email ?? "" } : null;
      setUser(u);
      if (!u) {
        wsStore.current = null;
        setWorkspaces([]);
        setActiveState(null);
        setRole(null);
        syncedFor = "";
        return;
      }
      const key = `${u.id}:${cityId}`;
      if (syncedFor !== key) {
        syncedFor = key;
        void loadWorkspaces(u);
        void sync(u, null);
      }
    };
    sb.auth.getSession().then(({ data }) => apply(data.session));
    const { data } = sb.auth.onAuthStateChange((_event, session) => apply(session));
    return () => {
      live = false;
      data.subscription.unsubscribe();
    };
    // sync/loadWorkspaces change identity with state; the effect needs only the client and the city.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityId]);

  const setActive = useCallback(
    (id: string | null) => {
      setActiveState(id);
      const s = stores(user);
      if (!s || !user) return;
      if (id) {
        s.ws.roleOf(id).then((r) => setRole(r)).catch(() => setRole(null));
      } else setRole(null);
      void sync(user, id);
    },
    [stores, user, sync]
  );

  const createWorkspace = useCallback(
    async (name: string) => {
      const s = stores(user);
      if (!s || !user || !name.trim()) return;
      try {
        const w = await s.ws.create(name.trim());
        setWorkspaces((list) => [...list, w]);
        setNotice(`Workspace "${w.name}" created`);
        setActive(w.id);
      } catch (e) {
        setNotice(e instanceof Error ? `Could not create the workspace: ${e.message}` : "Could not create the workspace");
      }
    },
    [stores, user, setActive]
  );

  const invite = useCallback(
    async (email: string, r: Exclude<Role, "owner">) => {
      const s = stores(user);
      if (!s || !user || !active) return;
      try {
        await s.ws.invite(active, email.trim(), r);
        setNotice(`Invited ${email.trim()} as ${r}`);
      } catch (e) {
        setNotice(e instanceof Error ? `Could not invite: ${e.message}` : "Could not invite");
      }
    },
    [stores, user, active]
  );

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
    setWorkspaces([]);
    setActiveState(null);
    setRole(null);
    setNotice("Signed out; your lines stay on this device");
  }, []);

  const allowed = active ? canEdit(role) : true;

  const pushLine = useCallback(
    async (s: Scenario) => {
      const st = stores(user);
      if (!st || !user) return;
      if (active && !canEdit(role)) {
        setNotice("You can view this workspace but not change it");
        return;
      }
      try {
        await st.lines.upsert([toRow({ ...s, ...(active ? { workspaceId: active } : {}) }, user.id)]);
      } catch (e) {
        setNotice(e instanceof Error ? `Cloud save failed: ${e.message}` : "Cloud save failed");
      }
    },
    [stores, user, active, role]
  );

  const removeLine = useCallback(
    async (id: string) => {
      const st = stores(user);
      if (!st || !user || (active && !canEdit(role))) return;
      try {
        await st.lines.remove(id);
      } catch {
        /* the local delete already happened; the next sync re-pulls if the cloud still has it */
      }
    },
    [stores, user, active, role]
  );

  return {
    configured,
    user,
    busy,
    notice,
    workspaces,
    active,
    role,
    canEdit: allowed,
    setActive,
    createWorkspace,
    invite,
    signIn,
    signOut,
    sync: () => sync(),
    pushLine,
    removeLine,
  };
}

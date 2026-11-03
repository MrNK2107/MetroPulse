/**
 * Team workspaces: a named space with members and roles. Lines saved into a workspace are
 * visible to every member; owners and editors can change them, viewers can only read.
 * Enforced in the database by row-level security (supabase/migrations/011_workspaces.sql);
 * mirrored here so the UI can hide what a viewer cannot do.
 */
import type { SupabaseClient } from "@supabase/supabase-js";

export type Role = "owner" | "editor" | "viewer";

export interface Workspace {
  id: string;
  name: string;
  ownerId: string;
  createdAt: string;
}

export interface Member {
  email: string;
  role: Role;
  userId: string | null;
}

export interface WorkspaceStore {
  list(): Promise<Workspace[]>;
  create(name: string): Promise<Workspace>;
  invite(workspaceId: string, email: string, role: Exclude<Role, "owner">): Promise<void>;
  members(workspaceId: string): Promise<Member[]>;
  roleOf(workspaceId: string): Promise<Role | null>;
}

export function canEdit(role: Role | null | undefined): boolean {
  return role === "owner" || role === "editor";
}

/** In-memory store: the test double and a stand-in for demos. */
export function memoryWorkspaces(me: { id: string; email: string }): WorkspaceStore {
  const spaces = new Map<string, Workspace>();
  const members = new Map<string, Member[]>();
  let n = 0;
  return {
    async list() {
      return Array.from(spaces.values()).filter((w) => (members.get(w.id) ?? []).some((m) => m.email === me.email || m.userId === me.id));
    },
    async create(name) {
      const w: Workspace = { id: `ws-${++n}`, name, ownerId: me.id, createdAt: new Date().toISOString() };
      spaces.set(w.id, w);
      members.set(w.id, [{ email: me.email, role: "owner", userId: me.id }]);
      return w;
    },
    async invite(workspaceId, email, role) {
      const list = members.get(workspaceId) ?? [];
      members.set(workspaceId, [...list.filter((m) => m.email !== email), { email, role, userId: null }]);
    },
    async members(workspaceId) {
      return members.get(workspaceId) ?? [];
    },
    async roleOf(workspaceId) {
      return (members.get(workspaceId) ?? []).find((m) => m.email === me.email || m.userId === me.id)?.role ?? null;
    },
  };
}

/** The production store over the `workspaces` and `workspace_members` tables. */
export function supabaseWorkspaces(sb: SupabaseClient, me: { id: string; email: string }): WorkspaceStore {
  const fail = (e: { message: string } | null) => {
    if (e) throw new Error(e.message);
  };
  return {
    async list() {
      const { data, error } = await sb.from("workspaces").select("id,name,owner_id,created_at");
      fail(error);
      return (data ?? []).map((w) => ({ id: w.id, name: w.name, ownerId: w.owner_id, createdAt: w.created_at }));
    },
    async create(name) {
      const { data, error } = await sb.from("workspaces").insert({ name, owner_id: me.id }).select("id,name,owner_id,created_at").single();
      fail(error);
      const m = await sb.from("workspace_members").insert({ workspace_id: data!.id, email: me.email, user_id: me.id, role: "owner" });
      fail(m.error);
      return { id: data!.id, name: data!.name, ownerId: data!.owner_id, createdAt: data!.created_at };
    },
    async invite(workspaceId, email, role) {
      const { error } = await sb.from("workspace_members").upsert({ workspace_id: workspaceId, email: email.toLowerCase(), role }, { onConflict: "workspace_id,email" });
      fail(error);
    },
    async members(workspaceId) {
      const { data, error } = await sb.from("workspace_members").select("email,role,user_id").eq("workspace_id", workspaceId);
      fail(error);
      return (data ?? []).map((m) => ({ email: m.email, role: m.role as Role, userId: m.user_id ?? null }));
    },
    async roleOf(workspaceId) {
      const { data, error } = await sb.from("workspace_members").select("role").eq("workspace_id", workspaceId).eq("email", me.email.toLowerCase()).maybeSingle();
      fail(error);
      return (data?.role as Role | undefined) ?? null;
    },
  };
}

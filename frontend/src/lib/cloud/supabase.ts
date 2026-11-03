/**
 * The optional cloud: Supabase Auth (magic links) and the `scenarios` table.
 * Configured only when both public env values are set; otherwise every helper reports
 * "not configured" and the desk stays local-first.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { CloudStore, ScenarioRow } from "./scenarioSync";

const URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const ANON = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

let client: SupabaseClient | null = null;

export function isCloudConfigured(): boolean {
  return Boolean(URL && ANON);
}

export function getSupabase(): SupabaseClient | null {
  if (!isCloudConfigured()) return null;
  if (!client) client = createClient(URL, ANON, { auth: { persistSession: true, autoRefreshToken: true } });
  return client;
}

/** The production store: the `scenarios` table under row-level security (see supabase/migrations/010_scenarios.sql). */
export function supabaseStore(sb: SupabaseClient): CloudStore {
  return {
    async list(cityId) {
      const { data, error } = await sb.from("scenarios").select("*").eq("city_id", cityId);
      if (error) throw new Error(error.message);
      return (data ?? []) as ScenarioRow[];
    },
    async upsert(rows) {
      const { error } = await sb.from("scenarios").upsert(rows, { onConflict: "id" });
      if (error) throw new Error(error.message);
    },
    async remove(id) {
      const { error } = await sb.from("scenarios").delete().eq("id", id);
      if (error) throw new Error(error.message);
    },
  };
}

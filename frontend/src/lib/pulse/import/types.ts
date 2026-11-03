import type { ModeId } from "../siting";

/** Every parser reports what it kept and dropped, or one error the user can act on. */
export type ParseResult<T> = { ok: true; value: T; report: string[] } | { ok: false; error: string };

export interface Station {
  name: string;
  lat: number;
  lng: number;
  mode: ModeId;
}

export const ok = <T>(value: T, report: string[] = []): ParseResult<T> => ({ ok: true, value, report });
export const fail = <T>(error: string): ParseResult<T> => ({ ok: false, error });

/** Map a user's mode word to a mode id; `bus` means a feeder bus stop. */
export function modeFromWord(word: string | undefined, fallback: ModeId = "metro"): ModeId {
  const w = (word ?? "").trim().toLowerCase();
  if (w === "metro" || w === "rail" || w === "subway") return "metro";
  if (w === "brt") return "brt";
  if (w === "feeder" || w === "bus") return "feeder";
  return fallback;
}

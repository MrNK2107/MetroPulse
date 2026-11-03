/** The GTFS parse as a message handler: pure, so the worker file stays two lines and this is testable. */
import { parseGtfsZip } from "./gtfs";
import type { ParseResult, Station } from "./types";

export interface GtfsRequest {
  bytes: Uint8Array;
  centre: [number, number];
}

export function handleGtfsRequest(msg: GtfsRequest): ParseResult<Station[]> {
  try {
    if (!(msg?.bytes instanceof Uint8Array)) return { ok: false, error: "No file data received" };
    return parseGtfsZip(msg.bytes, msg.centre);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Could not read this feed" };
  }
}

/** Parse on the calling thread. Used when Workers are unavailable, and as the Jest stand-in for the worker client. */
import { handleGtfsRequest } from "./gtfsWorkerHandler";
import type { ParseResult, Station } from "./types";

export function parseGtfsOffThread(bytes: Uint8Array, centre: [number, number]): Promise<ParseResult<Station[]>> {
  return Promise.resolve(handleGtfsRequest({ bytes, centre }));
}

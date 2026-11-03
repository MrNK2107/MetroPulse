/**
 * Parse a GTFS zip in a Web Worker so a feed of hundreds of megabytes does not freeze the desk.
 * Falls back to the calling thread when Workers are unavailable or the worker fails to start.
 * (Jest maps this module to the inline version; see jest.config.js.)
 */
import { parseGtfsOffThread as inline } from "./gtfsWorkerClient.inline";
import type { ParseResult, Station } from "./types";

export function parseGtfsOffThread(bytes: Uint8Array, centre: [number, number]): Promise<ParseResult<Station[]>> {
  if (typeof Worker === "undefined") return inline(bytes, centre);
  return new Promise((resolve) => {
    let worker: Worker;
    try {
      worker = new Worker(new URL("./gtfs.worker.ts", import.meta.url));
    } catch {
      resolve(inline(bytes, centre));
      return;
    }
    const done = (r: ParseResult<Station[]>) => {
      worker.terminate();
      resolve(r);
    };
    worker.onmessage = (e: MessageEvent<ParseResult<Station[]>>) => done(e.data);
    worker.onerror = () => done({ ok: false, error: "The feed could not be parsed in the background; try a smaller zip" });
    // The buffer is transferred, not copied; the caller does not use it again.
    worker.postMessage({ bytes, centre }, [bytes.buffer]);
  });
}

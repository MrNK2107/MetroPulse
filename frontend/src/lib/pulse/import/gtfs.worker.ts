/// <reference lib="webworker" />
import { GtfsRequest, handleGtfsRequest } from "./gtfsWorkerHandler";

declare const self: DedicatedWorkerGlobalScope;

self.onmessage = (e: MessageEvent<GtfsRequest>) => {
  self.postMessage(handleGtfsRequest(e.data));
};

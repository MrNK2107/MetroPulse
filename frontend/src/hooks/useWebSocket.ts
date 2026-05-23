"use client";

import { useCallback, useRef } from "react";
import { WebSocketClient } from "@/lib/ws";
import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationParams } from "@/types/simulation";

export function useWebSocket() {
  const clientRef = useRef<WebSocketClient | null>(null);
  const {
    addFrame,
    setInsight,
    setStatus,
    setError,
    setSimulationId,
    reset,
  } = useSimulationStore();

  const startSimulation = useCallback(
    (params: SimulationParams, wsUrl: string) => {
      reset();

      const client = new WebSocketClient(wsUrl, {
        onFrame: (msg) => {
          addFrame(msg.payload);
        },
        onInsight: (msg) => {
          setInsight(msg.markdown);
        },
        onError: (msg) => {
          setError(msg.message);
        },
        onDone: (msg) => {
          setStatus("done");
          setSimulationId(msg.simulationId);
        },
      });

      clientRef.current = client;
      setStatus("running");
      client.connect(params);
    },
    [addFrame, setInsight, setStatus, setError, setSimulationId, reset]
  );

  const stopSimulation = useCallback(() => {
    clientRef.current?.disconnect();
    setStatus("idle");
  }, [setStatus]);

  return { startSimulation, stopSimulation };
}

"use client";

import { useCallback, useRef } from "react";
import { WebSocketClient } from "@/lib/ws";
import { useSimulationStore } from "@/store/simulationStore";

export function useWebSocket() {
  const clientRef = useRef<WebSocketClient | null>(null);

  const startSimulation = useCallback(
    (scenario: string, wsUrl: string) => {
      const store = useSimulationStore.getState();
      store.resetRun();
      const client = new WebSocketClient(wsUrl, {
        onStage: (msg) => useSimulationStore.getState().setStage(msg.stage, msg.message),
        onParsed: (msg) => {
          useSimulationStore.getState().setParsedScenario(msg.params);
          if (msg.boundary) {
            useSimulationStore.getState().setRegionBoundary(msg.boundary);
          }
        },
        onPrediction: (msg) => useSimulationStore.getState().setPrediction(msg.prediction),
        onFrame: (msg) => useSimulationStore.getState().addFrame(msg.payload),
        onCaseStudies: (msg) => useSimulationStore.getState().setCaseStudies(msg.studies),
        onEvidence: (msg) => useSimulationStore.getState().setEvidence(msg.evidence),
        onError: (msg) => useSimulationStore.getState().setError(msg.message, msg.stage as any),
        onDone: (msg) => useSimulationStore.getState().setSimulationId(msg.simulationId),
      });

      clientRef.current = client;
      client.connect(scenario);
    },
    []
  );

  const stopSimulation = useCallback(() => {
    clientRef.current?.disconnect();
    useSimulationStore.getState().setError("Simulation stopped by user.");
  }, []);

  return { startSimulation, stopSimulation };
}

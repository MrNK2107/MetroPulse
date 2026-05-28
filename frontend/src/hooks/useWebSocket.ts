"use client";

import { useCallback, useRef } from "react";
import { WebSocketClient } from "@/lib/ws";
import { useSimulationStore } from "@/store/simulationStore";

export function useWebSocket() {
  const clientRef = useRef<WebSocketClient | null>(null);

  const startSimulation = useCallback(
    (scenario: string, wsUrl: string) => {
      if (!scenario || scenario.trim().length < 10) {
        useSimulationStore.getState().setError(
          "Please describe a scenario with at least 10 characters. Example: 'What happens to Hyderabad if pharma FDI drops 40%?'"
        );
        return;
      }

      // Disconnect any existing client before starting a new one
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }

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
        onNeedsInput: (msg) => {
          const store = useSimulationStore.getState();
          store.setPendingQuestion(msg);
          store.addConversationMessage("system", msg.question);
        },
        onGroupScores: (msg) => useSimulationStore.getState().setGroupScores(msg),
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

  const sendResponse = useCallback((text: string) => {
    const store = useSimulationStore.getState();
    store.addConversationMessage("user", text);
    store.setPendingQuestion(null);
    const sent = clientRef.current?.sendInputResponse(text) ?? false;
    if (!sent) {
      store.setError("Could not send your response — connection lost. Please try again.");
    }
  }, []);

  return { startSimulation, stopSimulation, sendResponse };
}

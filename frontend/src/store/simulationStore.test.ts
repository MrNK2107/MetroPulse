import { useSimulationStore } from "./simulationStore";

// Reset store between tests
beforeEach(() => {
  useSimulationStore.getState().resetAll();
});

describe("simulationStore", () => {
  it("setScenarioText updates state", () => {
    useSimulationStore.getState().setScenarioText("test scenario");
    expect(useSimulationStore.getState().scenarioText).toBe("test scenario");
  });

  it("setStage appends to stageHistory and marks previous as complete", () => {
    const { setStage } = useSimulationStore.getState();
    setStage("parsing", "Parsing scenario");
    expect(useSimulationStore.getState().pipelineStage).toBe("parsing");
    expect(useSimulationStore.getState().stageHistory).toHaveLength(1);
    expect(useSimulationStore.getState().stageHistory[0].status).toBe("active");

    setStage("predicting", "Generating prediction");
    expect(useSimulationStore.getState().pipelineStage).toBe("predicting");
    expect(useSimulationStore.getState().stageHistory).toHaveLength(2);
    expect(useSimulationStore.getState().stageHistory[0].status).toBe("complete");
    expect(useSimulationStore.getState().stageHistory[1].status).toBe("active");
  });

  it("addFrame appends frame and updates metrics and index", () => {
    const frame = {
      month: 1,
      timestamp: "2026-01-01",
      cells: [],
      metrics: {
        gdpDelta: 0.05,
        unemploymentRate: 0.04,
        realEstateIndex: 1.0,
        transitCongestion: 0.3,
        informalEmployment: 0.2,
        housingAffordability: 0.6,
        floodDisruption: 0.0,
        migrationBalance: 0.0,
      },
      activeLoop: "primary",
      proof: { formula: "", dataQuality: "", cellCount: 0, activeEffects: [] },
    };
    useSimulationStore.getState().addFrame(frame as any);
    const state = useSimulationStore.getState();
    expect(state.frames).toHaveLength(1);
    expect(state.metrics).toHaveLength(1);
    expect(state.activeFrameIndex).toBe(0);
  });

  it("resetRun clears simulation data but keeps scenarioText", () => {
    const store = useSimulationStore.getState();
    store.setScenarioText("keep this");
    store.setStage("parsing", "test");
    store.resetRun();
    const state = useSimulationStore.getState();
    expect(state.scenarioText).toBe("keep this");
    expect(state.frames).toHaveLength(0);
    expect(state.pipelineStage).toBe("idle");
    expect(state.stageHistory).toHaveLength(0);
  });

  it("resetAll clears everything including scenarioText", () => {
    const store = useSimulationStore.getState();
    store.setScenarioText("clear this");
    store.resetAll();
    const state = useSimulationStore.getState();
    expect(state.scenarioText).not.toBe("clear this");
    expect(state.frames).toHaveLength(0);
    expect(state.pipelineStage).toBe("idle");
  });

  it("flyToCity updates mapViewState to correct city coords", () => {
    useSimulationStore.getState().flyToCity("bengaluru");
    const { mapViewState } = useSimulationStore.getState();
    expect(mapViewState.longitude).toBeCloseTo(77.5946, 2);
    expect(mapViewState.latitude).toBeCloseTo(12.9716, 2);
  });

  it("setParsedScenario auto-centers map on resolved city", () => {
    useSimulationStore.getState().setParsedScenario({
      city: "mumbai",
      sector_deltas: {},
      policies_active: [],
      public_works_zone: null,
      horizon_months: 24,
      causal_chain: "",
      keywords: [],
      confidence: "medium",
      assumptions: [],
    });
    const { mapViewState } = useSimulationStore.getState();
    expect(mapViewState.longitude).toBeCloseTo(72.8777, 2);
    expect(mapViewState.latitude).toBeCloseTo(19.076, 2);
  });

  it("setDrawMode resets pendingVertices", () => {
    const store = useSimulationStore.getState();
    store.addZoneVertex([1, 2]);
    store.setDrawMode("polygon");
    expect(useSimulationStore.getState().pendingVertices).toHaveLength(0);
    expect(useSimulationStore.getState().drawMode).toBe("polygon");
  });
});

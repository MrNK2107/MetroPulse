import { render, screen } from "@testing-library/react";
import { DataFreshnessPanel } from "./DataFreshnessPanel";
import { useSimulationStore } from "@/store/simulationStore";

describe("DataFreshnessPanel", () => {
  beforeEach(() => {
    useSimulationStore.getState().resetAll();
  });

  it("shows demo mode before a real snapshot is available", () => {
    render(<DataFreshnessPanel />);

    expect(screen.getByText("Synthetic Fallback")).toBeInTheDocument();
    expect(screen.getByText("Simulation Trust")).toBeInTheDocument();
    expect(screen.getByText("Mobility")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
  });

  it("shows degraded real-time status from parsed snapshot", () => {
    useSimulationStore.getState().setParsedScenario(
      {
        city: "bengaluru",
        sector_deltas: {},
        policies_active: [],
        public_works_zone: null,
        horizon_months: 24,
        causal_chain: "",
        keywords: [],
        confidence: "high",
        assumptions: [],
      },
      {
        id: "snap-1",
        city: "bengaluru",
        status: "degraded",
        qualityScore: 0.72,
        sourceManifest: {
          mobility: {
            domain: "mobility",
            source: "IUDX fixture",
            observed_at: "2026-05-29T00:00:00Z",
            fetched_at: "2026-05-29T00:00:00Z",
            freshness: "stale",
            confidence: 0.7,
            cadence_seconds: 60,
            license: "public",
            notes: "",
          },
        },
      }
    );

    render(<DataFreshnessPanel />);

    expect(screen.getByText("Data-Informed (Partial)")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "72%")).toBeInTheDocument();
    expect(screen.getByText("stale")).toBeInTheDocument();
  });
});

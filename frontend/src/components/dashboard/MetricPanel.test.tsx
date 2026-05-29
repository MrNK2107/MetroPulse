import { fireEvent, render, screen } from "@testing-library/react";
import type React from "react";
import { MetricPanel } from "./MetricPanel";
import { useSimulationStore } from "@/store/simulationStore";

jest.mock("@tremor/react", () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  AreaChart: () => <div data-testid="area-chart" />,
  Title: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <h3 className={className}>{children}</h3>
  ),
  Text: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <p className={className}>{children}</p>
  ),
}));

const frame = {
  month: 1,
  cells: [],
  metrics: {
    gdpDelta: 0.042,
    unemploymentRate: 0.051,
    realEstateIndex: 1.02,
    transitCongestion: 0.36,
    informalEmployment: 0.18,
    housingAffordability: 0.94,
    floodDisruption: 0.01,
    migrationBalance: 0.02,
  },
  metric_metadata: {
    gdpDelta: {
      value: 0.042,
      confidence: 0.63,
      confidence_label: "Medium",
      origin: "estimated",
      sources: ["city_baseline_yaml", "rag_evidence_pack"],
    },
  },
  proof: {
    formula: "",
    dataQuality: "Estimated model output",
    cellCount: 0,
    activeEffects: [],
  },
};

describe("MetricPanel", () => {
  beforeEach(() => {
    useSimulationStore.getState().resetAll();
  });

  it("shows confidence metadata on major metric cards", () => {
    useSimulationStore.getState().addFrame(frame as any);

    render(<MetricPanel />);

    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByTitle(/not a probability/i)).toBeInTheDocument();
    expect(screen.queryByText("LIVE")).not.toBeInTheDocument();
  });

  it("uses scenario-estimate wording in detailed charts", () => {
    useSimulationStore.getState().addFrame(frame as any);

    render(<MetricPanel />);
    fireEvent.click(screen.getByText("Show Detailed Charts"));

    expect(screen.getByText(/Confidence: Medium/i)).toBeInTheDocument();
    expect(screen.getByText(/Origin: estimated/i)).toBeInTheDocument();
  });
});

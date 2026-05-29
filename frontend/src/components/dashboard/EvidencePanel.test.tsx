import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { EvidencePanel } from "./EvidencePanel";
import { useSimulationStore } from "@/store/simulationStore";

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: jest.fn(),
}));

const baseEvidence = {
  simple_markdown: "",
  markdown: "## Simulation Results\n\nNo close historical precedent found for this scenario; evidence relies on simulation outputs.",
  translation: {
    headline: "",
    sector_impacts: [],
    takeaways: [],
    gdp_summary: "",
    unemployment_summary: "",
    overall_verdict: "",
  },
  verdict: "Partially Confirmed",
  metrics: {
    gdpDelta: 0,
    unemploymentRate: 0.05,
    realEstateIndex: 1,
    transitCongestion: 0.4,
    informalEmployment: 0.2,
    housingAffordability: 0.6,
    floodDisruption: 0,
    migrationBalance: 0,
  },
  proof: {
    formula: "",
    dataQuality: "Demo data",
    cellCount: 10,
    activeEffects: [],
  },
  assumptions: [],
  explainability: {
    summary: "Hyderabad shows a scenario-estimated decrease in modeled activity.",
    confidence: 0.62,
    confidence_label: "Medium" as const,
    top_drivers: [
      { factor: "Scenario sector shock: Manufacturing", contribution: 42, origin: "scenario_input" },
    ],
    limitations: ["This is a model estimate, not a prediction."],
  },
  case_retrieval: {
    query_city: "hyderabad",
    query_sectors: ["manufacturing"],
    query_policies: ["Make in India"],
    returned_count: 1,
    omitted_weak_count: 3,
    retrieval_mode: "strict" as const,
  },
};

describe("EvidencePanel", () => {
  beforeEach(() => {
    useSimulationStore.getState().resetAll();
  });

  it("shows case match reasons", () => {
    useSimulationStore.getState().setEvidence(baseEvidence as any);
    useSimulationStore.getState().setCaseStudies([
      {
        id: "hyderabad-pharma-sez",
        title: "Hyderabad Pharma and Genome Valley SEZ Expansion",
        city: "Hyderabad",
        year: 2022,
        description: "Pharma cluster investment.",
        outcome: "Manufacturing growth produced jobs.",
        source: "Telangana reports",
        source_type: "government",
        tags: ["pharma"],
        sectors: ["manufacturing"],
        policies: ["Make in India"],
        relevance_score: 120,
        relevance_tier: "exact",
        match_reasons: ["Same city", "Manufacturing", "Make in India"],
        matched_city: true,
        matched_sectors: ["manufacturing"],
        matched_policies: ["Make in India"],
      },
    ]);

    render(<EvidencePanel />);
    fireEvent.click(screen.getByText("Cases"));

    expect(screen.getByText("Same city")).toBeInTheDocument();
    expect(screen.getByText("Manufacturing")).toBeInTheDocument();
    expect(screen.getByText("Make in India")).toBeInTheDocument();
  });

  it("shows case retrieval audit metadata", () => {
    useSimulationStore.getState().setEvidence(baseEvidence as any);

    render(<EvidencePanel />);
    fireEvent.click(screen.getByText("Technical"));

    expect(screen.getByText("Case Retrieval Audit")).toBeInTheDocument();
    expect(screen.getByText("Strict Precedent Matching")).toBeInTheDocument();
    expect(screen.getByText("Manufacturing")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders why-this-result explainability", () => {
    useSimulationStore.getState().setEvidence({
      ...baseEvidence,
      translation: {
        ...baseEvidence.translation,
        headline: "Scenario estimate",
        sector_impacts: [
          {
            sector: "manufacturing",
            sector_label: "Manufacturing",
            delta_pct: -20,
            direction: "negative",
            headline: "Manufacturing declines",
            person_example: "A factory worker may see fewer shifts.",
            city_wide: "Industrial activity softens.",
            numbers: {},
          },
        ],
      },
    } as any);

    render(<EvidencePanel />);

    expect(screen.getByText("Why this result?")).toBeInTheDocument();
    expect(screen.getByText(/scenario-estimated decrease/)).toBeInTheDocument();
    expect(screen.getByText(/Confidence: Medium/)).toBeInTheDocument();
  });
});

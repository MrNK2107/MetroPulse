export const SECTOR_LABELS: Record<string, string> = {
  it_ites: "IT/ITES",
  manufacturing: "Manufacturing",
  real_estate: "Real Estate",
  trade_hospitality: "Trade & Hospitality",
  transport_logistics: "Transport & Logistics",
  informal: "Informal Economy",
  public_admin: "Public Administration",
};

export type PipelineStage =
  | "idle"
  | "parsing"
  | "predicting"
  | "simulating"
  | "retrieving"
  | "synthesizing"
  | "done"
  | "error";

export interface ParsedScenario {
  city: string;
  sector_deltas: Record<string, number>;
  policies_active: string[];
  public_works_zone: GeoJSON.GeoJSON | null;
  horizon_months: 6 | 12 | 24 | 60;
  causal_chain: string;
  keywords: string[];
  confidence: "high" | "medium" | "low";
  assumptions: string[];
}

export interface SectorPrediction {
  direction: "up" | "down" | "stable";
  magnitude: "low" | "moderate" | "high";
  confidence: "high" | "medium" | "low";
  rationale: string;
}

export interface Prediction {
  employment_impact: Record<string, SectorPrediction>;
  real_estate_impact: Record<string, unknown>;
  transit_impact: Record<string, unknown>;
  most_affected_areas: string[];
  counter_intuitive: string[];
  overall_confidence: "high" | "medium" | "low";
  reasoning: string;
}

export interface CaseStudy {
  id: string;
  title: string;
  city: string;
  year: number;
  description: string;
  outcome: string;
  source: string;
  source_type: string;
  tags: string[];
  sectors: string[];
  policies: string[];
  relevance_score: number;
}

export interface HexCellState {
  h3Index: string;
  economicActivity: number;
  delta: number;
  jobDensity: number;
  jobDensityInformal: number;
  realEstateIndex: number;
  congestion: number;
  housingAffordability: number;
  floodRisk: number;
  migrationPressure: number;
  visualCue: "growth" | "stress" | "stable" | "flood-risk";
  proof: string;
}

export interface AggregateMetrics {
  gdpDelta: number;
  unemploymentRate: number;
  realEstateIndex: number;
  transitCongestion: number;
  informalEmployment: number;
  housingAffordability: number;
  floodDisruption: number;
  migrationBalance: number;
}

export interface SimulationFrame {
  month: number;
  timestamp: string;
  cells: HexCellState[];
  metrics: AggregateMetrics;
  activeLoop: string;
  proof: {
    formula: string;
    dataQuality: string;
    cellCount: number;
    activeEffects: string[];
  };
}

export interface EvidenceReport {
  markdown: string;
  verdict: string;
  metrics: AggregateMetrics;
  proof: SimulationFrame["proof"];
  assumptions: string[];
}

export interface WSStartMessage {
  type: "START";
  scenario: string;
}

export interface WSStageMessage {
  type: "STAGE";
  stage: Exclude<PipelineStage, "idle" | "error">;
  message: string;
}

export interface WSParsedMessage {
  type: "PARSED";
  params: ParsedScenario;
  boundary?: GeoJSON.GeoJSON;
}

export interface WSPredictionMessage {
  type: "PREDICTION";
  prediction: Prediction;
}

export interface WSFrameMessage {
  type: "FRAME";
  payload: SimulationFrame;
}

export interface WSCaseStudiesMessage {
  type: "CASE_STUDIES";
  studies: CaseStudy[];
}

export interface WSEvidenceMessage {
  type: "EVIDENCE";
  evidence: EvidenceReport;
}

export interface WSErrorMessage {
  type: "ERROR";
  stage?: PipelineStage;
  code: string;
  message: string;
}

export interface WSDoneMessage {
  type: "DONE";
  simulationId: string;
}

export type WSMessage =
  | WSStageMessage
  | WSParsedMessage
  | WSPredictionMessage
  | WSFrameMessage
  | WSCaseStudiesMessage
  | WSEvidenceMessage
  | WSErrorMessage
  | WSDoneMessage;

export type MetricKey =
  | "gdpDelta"
  | "unemploymentRate"
  | "realEstateIndex"
  | "transitCongestion"
  | "informalEmployment"
  | "housingAffordability";

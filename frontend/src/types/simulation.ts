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
  | "group_scoring"
  | "done"
  | "error"
  | "needs_input";

export interface ParsedScenario {
  city: string;
  sector_deltas: Record<string, number>;
  policies_active: string[];
  public_works_zone: GeoJSON.GeoJSON | null;
  horizon_months: number;
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
  source?: "llm" | "deterministic_fallback";
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
  match_reasons?: string[];
  relevance_tier?: "exact" | "related" | "weak";
  matched_city?: boolean;
  matched_sectors?: string[];
  matched_policies?: string[];
}

export type DataDomain = "mobility" | "jobs" | "land_value" | "census" | "news";
export type FreshnessStatus = "fresh" | "stale" | "missing" | "demo";
export type SnapshotStatus = "fresh" | "degraded" | "unavailable" | "demo";

export interface SourceStatus {
  domain: DataDomain;
  source: string;
  observed_at: string | null;
  fetched_at: string | null;
  freshness: FreshnessStatus;
  confidence: number;
  cadence_seconds: number;
  license: string;
  notes: string;
}

export interface SnapshotSummary {
  id: string;
  city: string;
  status: SnapshotStatus;
  qualityScore: number;
  sourceManifest: Partial<Record<DataDomain, SourceStatus>>;
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
  confidence: number;
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

export interface MetricMetadata {
  value: number;
  confidence: number;
  confidence_label: "Low" | "Medium" | "High";
  origin: string;
  sources: string[];
}

export interface SimulationFrame {
  month: number;
  timestamp: string;
  cells: HexCellState[];
  metrics: AggregateMetrics;
  metric_metadata?: Partial<Record<keyof AggregateMetrics, MetricMetadata>>;
  activeLoop: string;
  proof: {
    formula: string;
    dataQuality: string;
    dataMode?: "real_time" | "demo";
    snapshotId?: string | null;
    qualityScore?: number;
    dataSources?: Partial<Record<DataDomain, SourceStatus>>;
    cellCount: number;
    activeEffects: string[];
    dataOrigins?: Record<string, string>;
    overallConfidence?: number;
    confidenceLabel?: "Low" | "Medium" | "High";
    overlaySummary?: {
      applied: boolean;
      modified_cells: number;
      origin: string;
      sources: string[];
      confidence: number;
    };
  };
}

export interface SectorImpact {
  sector: string;
  sector_label: string;
  delta_pct: number;
  direction: "positive" | "negative" | "mixed";
  headline: string;
  person_example: string;
  city_wide: string;
  numbers: Record<string, number>;
}

export interface TranslationResult {
  headline: string;
  sector_impacts: SectorImpact[];
  takeaways: string[];
  gdp_summary: string;
  unemployment_summary: string;
  overall_verdict: string;
}

export interface MetricExplanation {
  value: number;
  confidence: number;
  drivers: { factor: string; contribution_pct: number }[];
}

export interface EvidenceReport {
  simple_markdown: string;
  markdown: string;
  translation: TranslationResult;
  verdict: string;
  metrics: AggregateMetrics;
  proof: SimulationFrame["proof"];
  assumptions: string[];
  metric_metadata?: SimulationFrame["metric_metadata"];
  evidence_pack?: {
    scenario: string;
    query_terms: string[];
    items: Array<{
      id: string;
      title: string;
      summary: string;
      source_type: string;
      relevance: number;
      confidence: number;
      matched_sectors: string[];
    }>;
    coverage: Record<string, unknown>;
    overall_evidence_confidence: number;
  };
  explainability?: {
    summary: string;
    confidence: number;
    confidence_label: "Low" | "Medium" | "High";
    top_drivers: Array<{ factor: string; contribution: number; origin: string }>;
    limitations: string[];
  };
  explanation?: {
    gdp_delta?: MetricExplanation;
    unemployment?: MetricExplanation;
    real_estate?: MetricExplanation;
  };
  case_retrieval?: {
    query_city: string | null;
    query_sectors: string[];
    query_policies: string[];
    returned_count: number;
    omitted_weak_count: number;
    retrieval_mode: "strict";
  };
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
  snapshot?: SnapshotSummary;
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

export interface GroupImpact {
  name: string;
  purchasing_power: number;
  income_stability: number;
  expense_pressure: number;
  housing_impact: number;
  employment_impact: number;
  severity: "low" | "moderate" | "high";
}

export interface WSNeedsInputMessage {
  type: "NEEDS_INPUT";
  question: string;
  inferred_params: {
    city: string;
    sectors: { name: string; delta: number }[];
  };
  options: string[];
  mode: "quick" | "deep";
}

export interface WSGroupScoresMessage {
  type: "GROUP_SCORES";
  groups: GroupImpact[];
  citizen_satisfaction: number;
}

export type WSMessage =
  | WSStageMessage
  | WSParsedMessage
  | WSPredictionMessage
  | WSFrameMessage
  | WSCaseStudiesMessage
  | WSEvidenceMessage
  | WSErrorMessage
  | WSDoneMessage
  | WSNeedsInputMessage
  | WSGroupScoresMessage;

export type MetricKey =
  | "gdpDelta"
  | "unemploymentRate"
  | "realEstateIndex"
  | "transitCongestion"
  | "informalEmployment"
  | "housingAffordability";

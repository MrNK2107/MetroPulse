export interface FDIParams {
  tech: number;
  manufacturing: number;
  realEstate: number;
}

export interface SimulationParams {
  fdi: FDIParams;
  publicWorksZone: GeoJSON.GeoJSON | null;
  horizonMonths: 6 | 12 | 24 | 60;
}

export interface HexCellState {
  h3Index: string;
  economicActivity: number;
  delta: number;
  jobDensity: number;
  realEstateIndex: number;
  congestion: number;
}

export interface AggregateMetrics {
  gdpDelta: number;
  unemploymentRate: number;
  realEstateIndex: number;
  transitCongestion: number;
}

export interface SimulationFrame {
  month: number;
  timestamp: string;
  cells: HexCellState[];
  metrics: AggregateMetrics;
}

export interface WSStartMessage {
  type: "START";
  params: SimulationParams;
}

export interface WSFrameMessage {
  type: "FRAME";
  payload: SimulationFrame;
}

export interface WSInsightMessage {
  type: "INSIGHT";
  markdown: string;
}

export interface WSErrorMessage {
  type: "ERROR";
  code: string;
  message: string;
}

export interface WSDoneMessage {
  type: "DONE";
  simulationId: string;
}

export type WSMessage = WSFrameMessage | WSInsightMessage | WSErrorMessage | WSDoneMessage;

export type SimulationStatus = "idle" | "running" | "done" | "error";

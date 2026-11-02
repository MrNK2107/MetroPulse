export type TrustLabel = "fact" | "pattern" | "projection";

export interface PlaceMatch {
  placeId: string;
  name: string;
  level: string;
  stateCode: string | null;
  score: number;
  method: string;
}

export interface Resolution {
  matches: PlaceMatch[];
  ambiguous: boolean;
}

export interface Receipt {
  sourceId: string;
  sourceName: string;
  /** null when the source has no published dataset yet */
  datasetVersion: string | null;
  license: string | null;
  url: string | null;
}

export interface Observation {
  indicator: string;
  name: string;
  unit: string;
  period: string | null;
  value: number | null;
  trustLabel: TrustLabel | null;
  receipt: Receipt;
}

export interface PlaceDetail {
  placeId: string;
  name: string;
  level: string;
  parent: { placeId: string; name: string } | null;
  state: { placeId: string; name: string } | null;
}

export type BoundaryLevel = "country" | "state" | "district";

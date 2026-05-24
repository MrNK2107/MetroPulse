const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface Region {
  id: string;
  name: string;
  city: string;
  country: string;
  population: number;
}

export interface RegionBaseline {
  gdp_index: number;
  unemployment: number;
  real_estate_idx: number;
  transit_load: number;
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  const body = await res.json();
  if (!body.success) {
    throw new Error(body.error?.message || "API returned unsuccessful");
  }
  return body.data as T;
}

export function fetchRegions(): Promise<Region[]> {
  return fetchJSON<Region[]>(`${API_URL}/regions`);
}

export function fetchRegionBaseline(id: string): Promise<RegionBaseline> {
  return fetchJSON<RegionBaseline>(`${API_URL}/regions/${id}/baseline`);
}

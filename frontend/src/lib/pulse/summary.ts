/**
 * One city, summarised: the numbers and sentences the city page, the API and
 * the briefing headline share.
 */
import { detectIncidents, Incident } from "./alerts";
import { hourLabel } from "./time";
import type { CityModel } from "./model";
import { existingCoverage, MODES, suggestSites, walkCoverage } from "./siting";
import { nearPlace, placeName } from "./placeName";

export interface SuggestedSite {
  name: string;
  lat: number;
  lng: number;
  boardings: number;
  newBoardings: number;
  newShare: number;
  score: number;
  peakHour: number;
}

export interface CitySummary {
  id: string;
  name: string;
  state: string;
  population: number;
  /** Average weekday trips (trip ends / 2). */
  dailyTrips: number;
  peakHour: number;
  coverageNow: number;
  coverageAfter: number;
  incidents: { total: number; surges: number; drops: number };
  topIncidents: Incident[];
  suggested: SuggestedSite[];
  hubs: string[];
  headline: string;
  lede: string;
}

/** Percent with one decimal below 10%, where whole numbers would hide the change. */
export function pct(x: number): string {
  const v = x * 100;
  return `${v < 10 ? v.toFixed(1) : Math.round(v)}%`;
}

const inr = (n: number) => Math.round(n).toLocaleString("en-IN");

export function nextStationPhrase(bestPlace: string | null): string {
  return `the next station belongs ${bestPlace ? nearPlace(bestPlace) : "near the core"}`;
}

export function headlineFor(cityName: string, incidentCount: number, bestPlace: string | null): string {
  return `${cityName}: ${incidentCount} incidents this week, and ${nextStationPhrase(bestPlace)}`;
}

export function ledeFor(s: {
  cityName: string;
  population: number;
  dailyTrips: number;
  peakHour: number;
  coverageNow: number;
  coverageAfter: number;
  hubs: string[];
  surges: number;
  drops: number;
  proposal?: string;
}): string {
  const raise = s.proposal ?? "the three recommended metro sites below would raise that to";
  return (
    `${s.cityName}'s ${inr(s.population)} residents make about ${inr(s.dailyTrips)} trips on an average weekday, peaking at ${hourLabel(s.peakHour)}. ` +
    `Only ${pct(s.coverageNow)} of them live within ${MODES.metro.walkKm * 1000} m of a mapped interchange (${s.hubs.join(", ")}); ${raise} ${pct(s.coverageAfter)}. ` +
    `This week the detector found ${s.surges} surge${s.surges === 1 ? "" : "s"} and ${s.drops} drop${s.drops === 1 ? "" : "s"} against the four-week baseline.`
  );
}

export function citySummary(model: CityModel): CitySummary {
  const { city } = model;
  const covered = existingCoverage(model);
  const incidents = detectIncidents(model);
  const sites = suggestSites(model, "metro", 3, covered, model.calibration);
  const coverageNow = walkCoverage(model);
  const coverageAfter = walkCoverage(model, sites.map((s) => s.result));
  const hourly = model.cityHourly(model.baselineMean);
  let peakHour = 0;
  for (let h = 0; h < 24; h++) if (hourly[24 + h] > hourly[24 + peakHour]) peakHour = h;
  const dailyTrips = model.dailyTrips.reduce((a, b) => a + b, 0) / 2;
  const surges = incidents.filter((i) => i.kind === "surge").length;
  const drops = incidents.length - surges;
  const hubs = model.hubs.length <= 6 ? model.hubs.map((h) => h.name) : [`${model.hubs.length} stations`];
  const suggested: SuggestedSite[] = sites.map((s) => {
    const cell = model.grid.cells[s.cell];
    const { lat, lng } = model.grid.unproject(cell);
    return {
      name: placeName(model, cell),
      lat: Math.round(lat * 1e4) / 1e4,
      lng: Math.round(lng * 1e4) / 1e4,
      boardings: s.result.dailyBoardings,
      newBoardings: s.result.newBoardings,
      newShare: s.result.newShare,
      score: s.result.score,
      peakHour: s.result.peakHour,
    };
  });
  return {
    id: city.id,
    name: city.name,
    state: city.state,
    population: city.population,
    dailyTrips,
    peakHour,
    coverageNow,
    coverageAfter,
    incidents: { total: incidents.length, surges, drops },
    topIncidents: incidents.slice(0, 3),
    suggested,
    hubs,
    headline: headlineFor(city.name, incidents.length, suggested[0]?.name ?? null),
    lede: ledeFor({ cityName: city.name, population: city.population, dailyTrips, peakHour, coverageNow, coverageAfter, hubs, surges, drops }),
  };
}

"use client";

import { useEffect, useRef, useState } from "react";
import type { City } from "@/lib/pulse/geo";
import type { CityModel } from "@/lib/pulse/model";
import { parseBoundaryGeoJson, ringAreaKm2 } from "@/lib/pulse/import/geojson";
import { parseGtfsOffThread } from "@/lib/pulse/import/gtfsWorkerClient";
import { parseStationsCsv } from "@/lib/pulse/import/stations";
import { parseCountsDetailed } from "@/lib/pulse/import/counts";
import { parseZonesCsv } from "@/lib/pulse/import/zones";
import type { ParseResult } from "@/lib/pulse/import/types";
import { CityData, describeCityData } from "@/lib/pulse/userdata";
import { downloadText } from "@/lib/pulse/export";
import { fmtInt } from "./SitingPanel";

interface Props {
  open: boolean;
  city: City;
  model: CityModel;
  data: CityData | null;
  onChange: (data: CityData | null) => void;
  onClose: () => void;
}

type SectionId = "boundary" | "hubs" | "counts" | "zones";

/** The banner line: what is loaded, plus the calibration when there is one. */
export function dataStatus(model: CityModel): string {
  const base = describeCityData(model.data);
  if (!base) return "";
  const cal = model.calibration;
  const parts = (Object.keys(cal.factor) as (keyof typeof cal.factor)[])
    .filter((m) => cal.stations[m] >= 3)
    .map((m) => `${m} on ${cal.stations[m]} stations (×${cal.factor[m].toFixed(2)})`);
  return parts.length ? `${base} · Calibrated: ${parts.join(", ")}` : base;
}

function Section({
  id,
  title,
  blurb,
  accept,
  current,
  report,
  error,
  busy,
  onFile,
  onRemove,
  children,
}: {
  id: SectionId;
  title: string;
  blurb: string;
  accept: string;
  current: string | null;
  report: string[];
  error: string | null;
  busy: boolean;
  onFile: (file: File) => void;
  onRemove: () => void;
  children?: React.ReactNode;
}) {
  const inputId = `data-${id}`;
  return (
    <section aria-labelledby={`${inputId}-h`} className="border-t-2 border-ink pt-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 id={`${inputId}-h`} className="font-display text-lg font-semibold">
          {title}
        </h3>
        {current && (
          <button
            type="button"
            onClick={onRemove}
            className="font-mono text-[11px] uppercase tracking-widest underline decoration-ink/40 underline-offset-2 hover:decoration-ink"
          >
            Remove {title.toLowerCase()}
          </button>
        )}
      </div>
      <p className="mt-1 text-xs leading-relaxed text-ink-soft">{blurb}</p>
      <p className="mt-2 font-mono text-[11px] text-ink-soft">
        {current ? <span className="text-supply-deep">{current}</span> : <span className="text-ink-faint">Nothing loaded</span>}
      </p>
      <label htmlFor={inputId} className="mt-2 block">
        <span className="sr-only">{title} file</span>
        <input
          id={inputId}
          type="file"
          accept={accept}
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
            e.target.value = "";
          }}
          className="block w-full text-sm file:mr-3 file:border file:border-ink file:bg-paper file:px-2.5 file:py-1 file:text-sm file:font-medium hover:file:bg-paper-deep"
        />
      </label>
      {error && (
        <p role="alert" className="mt-2 border border-signal bg-signal/10 px-2 py-1 text-sm text-signal-deep">
          {error}
        </p>
      )}
      {report.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-4 font-mono text-[11px] text-ink-soft">
          {report.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      {children}
    </section>
  );
}

/** FileReader-based: Blob.text() and arrayBuffer() are missing in older browsers and in jsdom. */
function readFile(file: File, as: "text"): Promise<string>;
function readFile(file: File, as: "bytes"): Promise<Uint8Array>;
function readFile(file: File, as: "text" | "bytes"): Promise<string | Uint8Array> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onerror = () => reject(new Error("Could not read this file"));
    r.onload = () => resolve(as === "text" ? String(r.result) : new Uint8Array(r.result as ArrayBuffer));
    if (as === "text") r.readAsText(file);
    else r.readAsArrayBuffer(file);
  });
}

function pctError(observed: number, modelled: number): string {
  if (modelled <= 0) return "–";
  const e = (observed - modelled) / modelled;
  return `${e >= 0 ? "+" : ""}${Math.round(e * 100)}%`;
}

export function DataDrawer({ open, city, model, data, onChange, onClose }: Props) {
  const [errors, setErrors] = useState<Partial<Record<SectionId, string>>>({});
  const [reports, setReports] = useState<Partial<Record<SectionId, string[]>>>({});
  const [busy, setBusy] = useState<SectionId | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  // Uploads are async; a second file must build on whatever the first one produced.
  const latest = useRef<CityData | null>(data);
  latest.current = data;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    panel.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const base = (): CityData => latest.current ?? { version: 1, cityId: city.id, loadedAt: new Date().toISOString() };

  const apply = <T,>(id: SectionId, r: ParseResult<T>, build: (v: T) => Partial<CityData>) => {
    if (!r.ok) {
      setErrors((e) => ({ ...e, [id]: r.error }));
      setReports((x) => ({ ...x, [id]: [] }));
      return;
    }
    setErrors((e) => ({ ...e, [id]: undefined }));
    setReports((x) => ({ ...x, [id]: r.report }));
    const next: CityData = { ...base(), ...build(r.value), loadedAt: new Date().toISOString() };
    latest.current = next;
    onChange(next);
  };

  const load = async (id: SectionId, file: File) => {
    setBusy(id);
    try {
      if (id === "boundary") {
        const text = await readFile(file, "text");
        apply(id, parseBoundaryGeoJson(text, city.center), (ring) => ({ boundary: { source: file.name, ring } }));
      } else if (id === "hubs") {
        if (/\.zip$/i.test(file.name)) {
          const bytes = await readFile(file, "bytes");
          apply(id, await parseGtfsOffThread(bytes, city.center), (stations) => ({ hubs: { source: file.name, stations } }));
        } else {
          const text = await readFile(file, "text");
          apply(id, parseStationsCsv(text), (stations) => ({ hubs: { source: file.name, stations } }));
        }
      } else if (id === "zones") {
        const text = await readFile(file, "text");
        apply(id, parseZonesCsv(text), (rows) => ({ zones: { source: file.name, rows } }));
      } else {
        const text = await readFile(file, "text");
        apply(id, parseCountsDetailed(text), (d) => ({ counts: { source: file.name, rows: d.rows, ...(d.hourly ? { hourly: d.hourly } : {}) } }));
      }
    } catch (err) {
      setErrors((e) => ({ ...e, [id]: err instanceof Error ? err.message : "Could not read this file" }));
    } finally {
      setBusy(null);
    }
  };

  const remove = (id: SectionId) => {
    if (!data) return;
    const next: CityData = { ...data, loadedAt: new Date().toISOString() };
    delete next[id];
    setReports((x) => ({ ...x, [id]: [] }));
    setErrors((e) => ({ ...e, [id]: undefined }));
    onChange(next.boundary || next.hubs || next.counts || next.zones ? next : null);
  };

  const cal = model.calibration;
  const modes = (Object.keys(cal.factor) as (keyof typeof cal.factor)[]).filter((m) => cal.stations[m] > 0);
  const boundaryLabel = data?.boundary ? `${data.boundary.source} · ${fmtInt(ringAreaKm2(data.boundary.ring))} km²` : null;
  const hubsLabel = data?.hubs ? `${data.hubs.stations.length} stations from ${data.hubs.source}` : null;
  const countsLabel = data?.counts ? `${data.counts.rows.length} stations from ${data.counts.source}` : null;
  const zonesLabel = data?.zones ? `${data.zones.rows.length} zones from ${data.zones.source}` : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <button type="button" aria-label="Close" onClick={onClose} className="flex-1 bg-ink/40" />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="data-drawer-title"
        tabIndex={-1}
        className="paper-grain flex h-full w-full max-w-md flex-col overflow-y-auto border-l-2 border-ink text-ink shadow-[-8px_0_0_0_#16130F] focus:outline-none"
      >
        <div className="flex items-start justify-between gap-4 border-b-2 border-ink px-5 py-4">
          <div>
            <h2 id="data-drawer-title" className="font-display text-2xl font-semibold leading-tight">
              Your data
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-ink-soft">
              Files are read in this browser and only the derived data (a boundary, a list of stations, daily counts) is kept on
              this device. Nothing is uploaded.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-8 w-8 shrink-0 border border-ink font-mono text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
            aria-label="Close your data"
          >
            ×
          </button>
        </div>

        <div className="space-y-5 px-5 py-4">
          <Section
            id="boundary"
            title="Boundary"
            blurb={`A GeoJSON Polygon or MultiPolygon of the ${city.name} planning area. The largest polygon replaces the sample outline.`}
            accept=".geojson,.json,application/geo+json,application/json"
            current={boundaryLabel}
            report={reports.boundary ?? []}
            error={errors.boundary ?? null}
            busy={busy === "boundary"}
            onFile={(f) => load("boundary", f)}
            onRemove={() => remove("boundary")}
          />
          <Section
            id="hubs"
            title="Stations"
            blurb="A GTFS static zip (stops, routes, trips, stop_times) or a CSV with name, lat, lng and an optional mode (metro, brt, bus). These become the existing hubs for coverage and cannibalisation."
            accept=".zip,.csv,application/zip,text/csv"
            current={hubsLabel}
            report={reports.hubs ?? []}
            error={errors.hubs ?? null}
            busy={busy === "hubs"}
            onFile={(f) => load("hubs", f)}
            onRemove={() => remove("hubs")}
          />
          <Section
            id="zones"
            title="Zones"
            blurb="Survey zones (TAZ, wards) as a CSV: zone, lat, lng, residents, jobs[, radius_km]. Residents and jobs per hexagon then come from your zones instead of the sample field; the hourly shape stays the model's."
            accept=".csv,text/csv"
            current={zonesLabel}
            report={reports.zones ?? []}
            error={errors.zones ?? null}
            busy={busy === "zones"}
            onFile={(f) => load("zones", f)}
            onRemove={() => remove("zones")}
          />
          <Section
            id="counts"
            title="Counts"
            blurb="Observed daily boardings per station as a CSV: station, daily_boardings (or station, date, boardings; or station, hour, boardings). Names are matched to the loaded stations. With three or more matches per mode, siting boardings are scaled to them; counts by hour also give the weekday its observed hourly shape."
            accept=".csv,text/csv"
            current={countsLabel}
            report={reports.counts ?? []}
            error={errors.counts ?? null}
            busy={busy === "counts"}
            onFile={(f) => load("counts", f)}
            onRemove={() => remove("counts")}
          >
            {data?.counts && !data.hubs && (
              <p className="mt-2 text-xs text-signal-deep">Load the stations first: counts are matched to station names.</p>
            )}
            {cal.matched.length > 0 && (
              <div className="mt-3">
                <table aria-label="Observed versus modelled boardings" className="w-full text-xs">
                  <thead>
                    <tr className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                      <th className="py-1 text-left font-normal">Station</th>
                      <th className="py-1 text-right font-normal">Observed</th>
                      <th className="py-1 text-right font-normal">Modelled</th>
                      <th className="py-1 text-right font-normal">Error</th>
                    </tr>
                  </thead>
                  <tbody className="tabular">
                    {cal.matched.map((m, k) => (
                      <tr key={`${k}-${m.station}`} className="border-t border-ink/15">
                        <td className="py-1 pr-2">{m.station}</td>
                        <td className="py-1 text-right">{fmtInt(m.observed)}</td>
                        <td className="py-1 text-right">{fmtInt(m.modelled)}</td>
                        <td className="py-1 text-right">{pctError(m.observed, m.modelled)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 font-mono text-[11px] text-ink-soft">
                  {modes
                    .map((m) =>
                      cal.stations[m] >= 3
                        ? `${m}: × ${cal.factor[m].toFixed(2)} on ${cal.stations[m]} stations, IQR ±${Math.round(cal.iqr[m] * 100)}%`
                        : `${m}: ${cal.stations[m]} matched, needs 3 to calibrate`
                    )
                    .join(" · ")}
                </p>
              </div>
            )}
            {cal.unmatched.length > 0 && (
              <p className="mt-2 text-xs text-ink-soft">
                <span className="font-semibold">Not matched to a station:</span> {cal.unmatched.join(", ")}
              </p>
            )}
          </Section>
        </div>

        <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t-2 border-ink px-5 py-3">
          <button
            type="button"
            disabled={!data}
            onClick={() => data && downloadText(`metropulse-${city.id}-data.json`, JSON.stringify(data, null, 2), "application/json")}
            className="border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            Export data (JSON)
          </button>
          <button
            type="button"
            disabled={!data}
            onClick={() => {
              setReports({});
              setErrors({});
              onChange(null);
            }}
            className="text-sm underline decoration-ink/40 underline-offset-2 hover:decoration-ink disabled:opacity-40"
          >
            Clear all
          </button>
        </div>
      </div>
    </div>
  );
}

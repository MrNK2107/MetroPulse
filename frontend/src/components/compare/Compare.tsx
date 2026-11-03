"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getCity } from "@/lib/pulse/geo";
import { getCityModel } from "@/lib/pulse/model";
import { decodeScenario, encodeScenario, evaluateScenario, NetworkResult, Scenario } from "@/lib/pulse/scenario";
import { getScenario, listScenarios } from "@/lib/pulse/scenarioStore";
import { alternativesCsv, alternativesMarkdown } from "@/lib/pulse/alternatives";
import { downloadText } from "@/lib/pulse/export";
import { CityData, loadCityData } from "@/lib/pulse/userdata";
import { HexMap, Marker } from "@/components/desk/HexMap";
import { fmtInt } from "@/components/desk/SitingPanel";
import { Wordmark } from "@/components/desk/Wordmark";

type Side = { kind: "ok"; s: Scenario; r: NetworkResult } | { kind: "missing" } | { kind: "bad" } | { kind: "pending" };

const pct = (x: number) => `${(x * 100).toFixed(x * 100 < 10 ? 1 : 0)}%`;
const signed = (d: number, fmt: (x: number) => string) => (d === 0 ? "0" : `${d > 0 ? "+" : "−"}${fmt(Math.abs(d))}`);

interface Metric {
  label: string;
  get: (r: NetworkResult, s: Scenario) => number;
  fmt: (x: number) => string;
}

const METRICS: Metric[] = [
  { label: "Stations", get: (_, s) => s.stations.length, fmt: (x) => String(Math.round(x)) },
  { label: "Length", get: (r) => r.lengthKm, fmt: (x) => `${x.toFixed(1)} km` },
  { label: "Daily boardings", get: (r) => r.boardings, fmt: fmtInt },
  { label: "New share", get: (r) => r.newShare, fmt: pct },
  { label: "Walk-band coverage after", get: (r) => r.coverageAfter, fmt: pct },
  { label: "Residents in walk bands", get: (r) => r.residents, fmt: fmtInt },
  { label: "Jobs in walk bands", get: (r) => r.jobs, fmt: fmtInt },
  { label: "Capital cost", get: (r) => r.costCr, fmt: (x) => `₹${fmtInt(x)} cr` },
  { label: "Cost per daily boarding", get: (r) => r.costPerBoardingLakh, fmt: (x) => `₹${x.toFixed(2)} lakh` },
  { label: "Score", get: (r) => r.score, fmt: (x) => String(Math.round(x)) },
];

/** `s=` text decodes on the spot; a saved id resolves on this device after mount. */
function initialSide(text: string | undefined, cityId: string): Side {
  if (!text) return { kind: "missing" };
  const decoded = decodeScenario(text, cityId);
  if (decoded) return { kind: "pending" };
  return /^[a-z0-9]{8}$/.test(text) ? { kind: "pending" } : { kind: "bad" };
}

export function Compare({ cityId, a, b }: { cityId: string; a?: string; b?: string }) {
  const city = getCity(cityId) ?? getCity("chennai")!;
  const [userData, setUserData] = useState<CityData | null>(null);
  const [resolved, setResolved] = useState<{ a: Scenario | null | undefined; b: Scenario | null | undefined }>({ a: undefined, b: undefined });
  const [library, setLibrary] = useState<Scenario[]>([]);

  useEffect(() => {
    setUserData(loadCityData(city.id));
    const resolve = (text?: string) => (text ? getScenario(text) ?? decodeScenario(text, city.id) : undefined);
    setResolved({ a: resolve(a), b: resolve(b) });
    setLibrary(listScenarios(city.id));
  }, [a, b, city.id]);

  const model = getCityModel(city, userData);

  const sides = useMemo(() => {
    const build = (text: string | undefined, s: Scenario | null | undefined): Side => {
      if (!text) return { kind: "missing" };
      if (s === undefined) return initialSide(text, city.id);
      if (s === null) return { kind: "bad" };
      return { kind: "ok", s, r: evaluateScenario(model, s) };
    };
    return { A: build(a, resolved.a), B: build(b, resolved.b) };
  }, [a, b, resolved, model, city.id]);

  const rows = (["A", "B"] as const).flatMap((label) => {
    const side = sides[label];
    return side.kind === "ok" ? [{ label, s: side.s, r: side.r }] : [];
  });
  const both = sides.A.kind === "ok" && sides.B.kind === "ok" ? { a: sides.A, b: sides.B } : null;

  const hrefWith = (label: "A" | "B", value: string) => {
    const q = new URLSearchParams({ city: city.id });
    const av = label === "A" ? value : a;
    const bv = label === "B" ? value : b;
    if (av) q.set("a", av);
    if (bv) q.set("b", bv);
    return `/compare?${q.toString()}`;
  };

  const values = useMemo(() => new Float32Array(model.grid.cells.length).map((_, c) => model.dailyTrips[c]), [model]);
  const scaleMax = useMemo(() => Math.max(...Array.from(values)) || 1, [values]);

  return (
    <div className="paper-grain min-h-screen text-ink">
      <nav className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink px-4 py-3 sm:px-6">
        <Link href="/" className="focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <Wordmark />
        </Link>
        <div className="flex gap-4 text-sm">
          <Link href={`/desk?city=${city.id}&tab=siting`} className="underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
            Back to the desk
          </Link>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Alternatives analysis</p>
        <h1 className="mt-1 font-display text-3xl font-bold leading-tight sm:text-4xl">{city.name}: compare two lines</h1>
        <p className="mt-2 max-w-2xl text-sm text-ink-soft">
          Each option is scored on the same model with the same existing hubs. Boardings are net of each line&rsquo;s own
          cannibalisation; costs are the sketch table saved with each line.
        </p>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          {(["A", "B"] as const).map((label) => {
            const side = sides[label];
            return (
              <section key={label} aria-label={`Option ${label}`} className="border-2 border-ink">
                <div className="flex items-baseline justify-between border-b border-ink px-4 py-2">
                  <span className="font-display text-2xl font-bold text-supply">{label}</span>
                  <span className="truncate font-display text-lg font-semibold">
                    {side.kind === "ok" ? side.s.name : side.kind === "bad" ? "Unreadable" : side.kind === "missing" ? "Not chosen" : "…"}
                  </span>
                </div>
                {side.kind === "ok" ? (
                  <div className="aspect-[4/3] bg-paper-deep/40">
                    <HexMap
                      title={`Hexagon map of ${city.name}: option ${label}`}
                      grid={model.grid}
                      anchors={city.anchors}
                      values={values}
                      scaleMax={scaleMax}
                      hubs={userData?.hubs ? model.hubs : undefined}
                      line={side.s.stations.map((p) => model.grid.project(p.lat, p.lng))}
                      walk={new Set(side.r.stations.flatMap((s) => s.walkCells))}
                      markers={side.s.stations.map<Marker>((p, k) => ({
                        id: `${label}${k}`,
                        at: model.grid.project(p.lat, p.lng),
                        kind: "station",
                        text: String(k + 1),
                        label: `Station ${k + 1}`,
                      }))}
                      className="h-full w-full"
                    />
                  </div>
                ) : side.kind === "bad" ? (
                  <p className="p-4 text-sm text-signal-deep">That line could not be read. Check the link, or pick a saved line below.</p>
                ) : side.kind === "pending" ? (
                  <p className="p-4 text-sm text-ink-soft">Loading…</p>
                ) : (
                  <p className="p-4 text-sm text-ink-soft">Pick a saved scenario for option {label}, or build one on the desk and press Compare.</p>
                )}
                {side.kind !== "ok" && library.length > 0 && (
                  <ul className="divide-y divide-ink/15 border-t border-ink px-4">
                    {library.map((s) => (
                      <li key={s.id} className="py-1.5 text-sm">
                        <Link href={hrefWith(label, s.id)} className="underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
                          {s.name}
                        </Link>
                        <span className="ml-2 font-mono text-[11px] text-ink-soft">
                          {s.stations.length} station{s.stations.length === 1 ? "" : "s"} · {s.mode}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            );
          })}
        </div>

        {rows.length > 0 && (
          <section aria-labelledby="table-h" className="mt-8">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h2 id="table-h" className="font-display text-2xl font-semibold">
                Alternatives table
              </h2>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => downloadText(`metropulse-${city.id}-alternatives.csv`, alternativesCsv(rows))}
                  className="border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
                >
                  Download CSV
                </button>
                <button
                  type="button"
                  onClick={() => downloadText(`metropulse-${city.id}-alternatives.md`, alternativesMarkdown(rows), "text/markdown;charset=utf-8")}
                  className="border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
                >
                  Download Markdown
                </button>
              </div>
            </div>
            <table aria-label="Alternatives" className="mt-3 w-full border-t-2 border-ink text-sm">
              <thead>
                <tr className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                  <th scope="col" className="py-1.5 text-left font-normal"></th>
                  <th scope="col" className="py-1.5 text-right font-normal">A</th>
                  <th scope="col" className="py-1.5 text-right font-normal">B</th>
                  <th scope="col" className="py-1.5 text-right font-normal">B − A</th>
                </tr>
              </thead>
              <tbody className="tabular">
                {METRICS.map((m) => {
                  const va = sides.A.kind === "ok" ? m.get(sides.A.r, sides.A.s) : null;
                  const vb = sides.B.kind === "ok" ? m.get(sides.B.r, sides.B.s) : null;
                  return (
                    <tr key={m.label} className="border-t border-ink/15">
                      <th scope="row" className="py-1.5 text-left font-medium">
                        {m.label}
                      </th>
                      <td className="py-1.5 text-right">{va === null ? "–" : m.fmt(va)}</td>
                      <td className="py-1.5 text-right">{vb === null ? "–" : m.fmt(vb)}</td>
                      <td className="py-1.5 text-right text-ink-soft">{both && va !== null && vb !== null ? signed(vb - va, m.fmt) : "–"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {rows.map((row) => (
              <p key={row.label} className="mt-2 bg-paper-deep px-2 py-1.5 font-mono text-[11px] leading-relaxed">
                {row.label}: {row.r.formula}; {row.r.costFormula}
              </p>
            ))}
            <p className="mt-3 text-xs text-ink-soft">
              Share this comparison by copying the address bar: both lines are encoded in the link. Lines named by a saved id
              exist only on this device.{" "}
              {both && (
                <Link href={`/compare?city=${city.id}&a=${encodeURIComponent(encodeScenario(both.a.s))}&b=${encodeURIComponent(encodeScenario(both.b.s))}`} className="underline">
                  Self-contained link
                </Link>
              )}
            </p>
          </section>
        )}
      </main>
    </div>
  );
}

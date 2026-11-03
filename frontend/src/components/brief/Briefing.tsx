"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getCity } from "@/lib/pulse/geo";
import { getCityModel, HOURS_PER_WEEK, dayHourLabel, hourLabel } from "@/lib/pulse/model";
import { detectIncidents } from "@/lib/pulse/alerts";
import { existingCoverage, MODES, suggestSites, walkCoverage } from "@/lib/pulse/siting";
import { HexMap } from "@/components/desk/HexMap";
import { nearPlace, placeName } from "@/components/desk/DeskApp";
import { fmtInt } from "@/components/desk/SitingPanel";
import { Wordmark } from "@/components/desk/Wordmark";
import { CityData, describeCityData, loadCityData } from "@/lib/pulse/userdata";

function Figure({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="border-t-2 border-ink pt-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">{label}</div>
      <div className="font-display text-3xl font-bold leading-tight tabular">{value}</div>
      <div className="text-xs text-ink-soft">{note}</div>
    </div>
  );
}

/** Percent with one decimal below 10%, where whole numbers would hide the change. */
function pct(x: number): string {
  const v = x * 100;
  return `${v < 10 ? v.toFixed(1) : Math.round(v)}%`;
}

export function Briefing({ cityId }: { cityId: string }) {
  const city = getCity(cityId) ?? getCity("chennai")!;
  const [userData, setUserData] = useState<CityData | null>(null);
  useEffect(() => {
    setUserData(loadCityData(city.id));
  }, [city.id]);
  const model = getCityModel(city, userData);
  const data = useMemo(() => {
    const covered = existingCoverage(model);
    const incidents = detectIncidents(model);
    const sites = suggestSites(model, "metro", 3, covered, model.calibration);
    const coverNow = walkCoverage(model);
    const coverAfter = walkCoverage(model, sites.map((s) => s.result));
    const hubs = model.hubs.length <= 6 ? model.hubs.map((h) => h.name) : [`${model.hubs.length} stations`];
    const hourly = model.cityHourly(model.baselineMean);
    let peak = 0;
    for (let h = 0; h < 24; h++) if (hourly[24 + h] > hourly[24 + peak]) peak = h;
    const dailyTrips = model.dailyTrips.reduce((a, b) => a + b, 0);
    const cores = model
      .rankCellsByDailyTrips()
      .slice(0, 5)
      .map((c) => ({ c, name: placeName(model, model.grid.cells[c]), trips: model.dailyTrips[c] }));
    const values = new Float32Array(model.grid.cells.length);
    for (let c = 0; c < values.length; c++) values[c] = model.dailyTrips[c];
    let max = 0;
    values.forEach((v) => (max = Math.max(max, v)));
    return { incidents, sites, coverNow, coverAfter, hubs, peak, dailyTrips, cores, values, max };
  }, [model, city]);

  const surge = data.incidents.filter((i) => i.kind === "surge").length;
  const drop = data.incidents.length - surge;
  const best = data.sites[0];

  return (
    <div className="paper-grain min-h-screen text-ink">
      <div className="no-print flex items-center justify-between border-b border-ink/30 px-4 py-2 sm:px-8">
        <Link href={`/desk?city=${city.id}`} className="text-sm underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
          Back to the desk
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="border-2 border-ink bg-ink px-3 py-1.5 text-sm font-semibold text-paper hover:border-signal hover:bg-signal focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
        >
          Print or save as PDF
        </button>
      </div>

      <article className="mx-auto max-w-[860px] px-5 py-8 sm:px-8">
        <header className="border-b-4 border-double border-ink pb-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Wordmark size={24} />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-soft">
              City briefing · {userData ? "your data" : "sample week"}
            </span>
          </div>
          <h1 className="mt-5 font-display text-4xl font-bold leading-[1.05] sm:text-5xl">
            {city.name}: {data.incidents.length} incidents this week, and the next station belongs {best ? nearPlace(placeName(model, model.grid.cells[best.cell])) : "near the core"}
          </h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-ink-soft">
            {city.name}&rsquo;s {fmtInt(city.population)} residents make about {fmtInt(data.dailyTrips / 2)} trips on an average
            weekday, peaking at {hourLabel(data.peak)}. Only {pct(data.coverNow)} of them live within {MODES.metro.walkKm * 1000} m
            of a mapped interchange ({data.hubs.join(", ")}); the three recommended metro sites below would raise that to{" "}
            {pct(data.coverAfter)}. This week the detector found {surge} surge
            {surge === 1 ? "" : "s"} and {drop} drop{drop === 1 ? "" : "s"} against the four-week baseline.
          </p>
        </header>

        <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <Figure label="Residents" value={`${(city.population / 1e6).toFixed(1)}M`} note="published city population" />
          <Figure label="Weekday trips" value={`${(data.dailyTrips / 2 / 1e6).toFixed(1)}M`} note={`peak hour ${hourLabel(data.peak)}`} />
          <Figure
            label="Walk-band coverage"
            value={`${pct(data.coverNow)} → ${pct(data.coverAfter)}`}
            note={`residents within ${MODES.metro.walkKm} km: today → with the 3 sites`}
          />
          <Figure label="Incidents" value={String(data.incidents.length)} note={`${surge} surge${surge === 1 ? "" : "s"} · ${drop} drop${drop === 1 ? "" : "s"}`} />
        </div>

        <figure className="mt-8 grid gap-4 sm:grid-cols-[1fr_260px]">
          <div className="aspect-square border border-ink bg-paper">
            <HexMap
              title={`Weekday demand map of ${city.name}`}
              grid={model.grid}
              anchors={city.anchors}
              values={data.values}
              scaleMax={data.max}
              markers={data.sites.map((s, k) => ({
                id: `s${k}`,
                at: model.grid.cells[s.cell],
                kind: "pick" as const,
                text: String(k + 1),
                label: `Recommended site ${k + 1}`,
              }))}
              className="h-full w-full"
            />
          </div>
          <figcaption className="space-y-3 text-sm">
            <p className="font-display text-lg font-semibold leading-snug">Where the city moves</p>
            <p className="text-ink-soft">
              Average weekday trips per hexagon (about 0.74 km² each). Darker is busier. Squares are existing transport hubs,
              numbered rings are the recommended metro sites.
            </p>
            <table className="w-full text-left text-[13px]">
              <caption className="pb-1 text-left font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
                Busiest demand cores
              </caption>
              <tbody>
                {data.cores.map((c, k) => (
                  <tr key={c.c} className="border-t border-ink/15">
                    <td className="py-1 pr-2 font-mono text-ink-faint">{k + 1}</td>
                    <td className="py-1">{c.name}</td>
                    <td className="py-1 text-right font-mono tabular">{fmtInt(c.trips)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </figcaption>
        </figure>

        <section aria-labelledby="brief-incidents" className="mt-10">
          <h2 id="brief-incidents" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            This week&apos;s incidents
          </h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {data.incidents.map((i) => (
              <article key={i.id} className={`border-l-4 pl-3 ${i.kind === "surge" ? "border-signal" : "border-supply"}`}>
                <h3 className="font-display text-lg font-semibold leading-snug">{i.headline}</h3>
                <p className="mt-1 text-sm leading-relaxed">{i.explanation}</p>
                <p className="mt-1 text-sm leading-relaxed">
                  <span className="font-semibold">Likely cause: </span>
                  {i.likelyCause}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                  <span className="font-semibold text-ink">Check: </span>
                  {i.whatToCheck}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="brief-sites" className="mt-10 break-inside-avoid">
          <h2 id="brief-sites" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            Recommended sites
          </h2>
          <p className="mt-2 text-sm text-ink-soft">
            Greedy search over every hexagon for a metro station ({MODES.metro.walkKm * 1000} m walk band,{" "}
            {MODES.metro.feederKm} km feeder band). Each site counts only demand that existing hubs and the sites above it do not
            already serve.
          </p>
          <table className="mt-3 w-full text-left text-sm">
            <thead>
              <tr className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
                <th className="py-1 pr-2 font-normal">#</th>
                <th className="py-1 font-normal">Location</th>
                <th className="py-1 text-right font-normal">New boardings / day</th>
                <th className="py-1 text-right font-normal">Peak</th>
                <th className="py-1 text-right font-normal">Score</th>
              </tr>
            </thead>
            <tbody>
              {data.sites.map((s, k) => (
                <tr key={s.cell} className="border-t border-ink/20">
                  <td className="py-1.5 pr-2 font-display text-lg font-bold text-supply">{k + 1}</td>
                  <td className="py-1.5">{placeName(model, model.grid.cells[s.cell])}</td>
                  <td className="py-1.5 text-right font-mono tabular">{fmtInt(s.result.newBoardings)}</td>
                  <td className="py-1.5 text-right font-mono">{hourLabel(s.result.peakHour)}</td>
                  <td className="py-1.5 text-right font-display text-lg font-bold tabular">{s.result.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section aria-labelledby="brief-method" className="mt-10 break-inside-avoid text-sm leading-relaxed">
          <h2 id="brief-method" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            Methodology and data
          </h2>
          <div className="mt-3 grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <p>
                <span className="font-semibold">Grid.</span> {fmtInt(model.grid.cells.length)} hexagons of{" "}
                {model.grid.cellAreaKm2.toFixed(2)} km² (H3 resolution 8 scale) inside the city boundary.
              </p>
              <p>
                <span className="font-semibold">Alerts.</span> Each hex-hour is compared with the same hour in the four trailing
                weeks (median and MAD). A hex-hour is flagged at robust z ≥ 4 and a change of at least 30%. Flagged hex-hours
                touching in space or time form one incident; the cause comes from a fixed rule trace.
              </p>
              <p>
                <span className="font-semibold">Siting.</span> Score = 60 × min(1, boardings ÷ {fmtInt(MODES.metro.referenceBoardings)}) +
                40 × share of boardings that are new coverage.
              </p>
            </div>
            <div className="space-y-2">
              {userData ? (
                <p>
                  <span className="font-semibold">Data.</span> {describeCityData(userData)}. Demand between stations is the
                  MetroPulse sample model (a seeded synthetic field built from {city.name}&rsquo;s configured anchor points and
                  published population){model.calibration.stations.metro >= 3
                    ? `, with metro boardings calibrated on ${model.calibration.stations.metro} stations (× ${model.calibration.factor.metro.toFixed(2)})`
                    : ""}
                  . The week contains scripted incidents.
                </p>
              ) : (
                <p>
                  <span className="font-semibold">Data.</span> Sample city model: a seeded synthetic demand field built from{" "}
                  {city.name}&rsquo;s configured anchor points ({city.anchors.map((a) => a.name).join(", ")}), its published
                  population and a sample outline drawn around those anchors (not the administrative boundary). The week contains
                  scripted incidents. Existing coverage counts only the mapped interchange{data.hubs.length === 1 ? "" : "s"} (
                  {data.hubs.join(", ")}), not every station on the network.
                </p>
              )}
              <p className="border border-signal bg-signal/10 p-2 text-ink">
                The algorithms are real. The numbers are illustrative until {city.name}&rsquo;s own data (boundary, stations,
                counts) is loaded on the desk under Your data and calibrated. Do not cite them as ridership forecasts.
              </p>
              <p className="font-mono text-[11px] text-ink-faint">Generated {dayHourLabel(0).slice(0, 3)}–Sun of the sample week · {HOURS_PER_WEEK} hours · MetroPulse</p>
            </div>
          </div>
        </section>
      </article>
    </div>
  );
}

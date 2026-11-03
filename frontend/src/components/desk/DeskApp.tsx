"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCity, listCities, Point } from "@/lib/pulse/geo";
import { CityModel, demandScaleMax, getCityModel, HOURS_PER_WEEK, dayHourLabel } from "@/lib/pulse/model";
import { detectIncidents, Incident } from "@/lib/pulse/alerts";
import { existingCoverage, ModeId, scoreSite, suggestSites, Suggestion } from "@/lib/pulse/siting";
import { HexMap, Marker } from "./HexMap";
import { Timeline } from "./Timeline";
import { AlertFeed } from "./AlertFeed";
import { SitingPanel, fmtInt } from "./SitingPanel";
import { Wordmark } from "./Wordmark";
import { Sparkline } from "./Sparkline";
import { ShortcutsHelp } from "./ShortcutsHelp";
import { useDeskShortcuts } from "./useDeskShortcuts";
import { cellDay, downloadText, incidentsToCsv } from "@/lib/pulse/export";
import { CityData, clearCityData, loadCityData, saveCityData } from "@/lib/pulse/userdata";
import { DataDrawer, dataStatus } from "./DataDrawer";
import { encodeScenario, Scenario, scenarioFromSuggestions } from "@/lib/pulse/scenario";
import { useLineScenario } from "./useLineScenario";

type Tab = "pulse" | "alerts" | "siting";
const TAB_ORDER: Tab[] = ["pulse", "alerts", "siting"];
const TABS: { id: Tab; label: string; verb: string }[] = [
  { id: "pulse", label: "Pulse", verb: "See" },
  { id: "alerts", label: "Alerts", verb: "Notice" },
  { id: "siting", label: "Siting", verb: "Decide" },
];

const COMPASS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"];

export function placeName(model: CityModel, p: Point): string {
  const { anchor, km } = model.nearestAnchor(p);
  if (km < 0.35) return anchor.name;
  const a = model.grid.project(anchor.lat, anchor.lng);
  const ang = (Math.atan2(p.y - a.y, p.x - a.x) * 180) / Math.PI;
  const dir = COMPASS[Math.round(((ang + 360) % 360) / 45) % 8];
  return `${km.toFixed(1)} km ${dir} of ${anchor.name}`;
}

/** "near T Nagar", but "0.8 km N of Chennai Central" (that is already a position). */
export function nearPlace(name: string): string {
  return /^\d/.test(name) ? name : `near ${name}`;
}

export interface DeskAppProps {
  initialCity: string;
  initialTab?: Tab;
  /** 1-based index into this week's incidents, as in a shared link. */
  initialIncident?: number;
  /** Open Siting with the three suggested sites and the best one pinned. */
  initialSuggest?: boolean;
  /** A line from the URL; `null` means the link carried one that could not be read. */
  initialScenario?: Scenario | null;
  /** A saved line's id, resolved on this device after mount. */
  initialScenarioId?: string;
}

export type { Tab as DeskTab };

/** The shareable URL for a desk view; the inverse of what app/desk/page.tsx parses. */
export function deskHref(cityId: string, tab: Tab, incident?: number, suggest?: boolean, line?: string): string {
  const q = new URLSearchParams({ city: cityId });
  if (tab !== "pulse") q.set("tab", tab);
  if (tab === "alerts" && incident) q.set("incident", String(incident));
  if (tab === "siting" && line) q.set("s", line);
  else if (tab === "siting" && suggest) q.set("suggest", "1");
  return `/desk?${q.toString()}`;
}

function initialState(cityId: string, incident?: number, suggest?: boolean) {
  const model = getCityModel(getCity(cityId)!);
  let selected: Incident | null = null;
  let hour = 24 + 9; // Tue 09:00
  let suggestions: Suggestion[] = [];
  let pin: Point | null = null;
  if (incident) {
    selected = detectIncidents(model)[incident - 1] ?? null;
    if (selected) hour = selected.peakHour;
  }
  if (suggest) {
    suggestions = suggestSites(model, "metro", 3, existingCoverage(model));
    if (suggestions[0]) {
      const c = model.grid.cells[suggestions[0].cell];
      pin = { x: c.x, y: c.y };
    }
  }
  return { selected, hour, suggestions, pin };
}

export function DeskApp({ initialCity, initialTab, initialIncident, initialSuggest, initialScenario, initialScenarioId }: DeskAppProps) {
  const startCity = getCity(initialCity) ? initialCity : "chennai";
  const [init] = useState(() => initialState(startCity, initialIncident, initialSuggest));
  const [cityId, setCityId] = useState(startCity);
  const [tab, setTab] = useState<Tab>(initialTab ?? "pulse");
  const [hour, setHour] = useState(init.hour);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState<Incident | null>(init.selected);
  const [mode, setMode] = useState<ModeId>("metro");
  const [pin, setPin] = useState<Point | null>(init.pin);
  const [suggestions, setSuggestions] = useState<Suggestion[]>(init.suggestions);
  const lastCity = useRef(startCity);
  const [helpOpen, setHelpOpen] = useState(false);
  const [dataOpen, setDataOpen] = useState(false);
  const [lineMode, setLineMode] = useState(Boolean(initialScenario || initialScenarioId));
  const [data, setData] = useState<CityData | null>(null);
  const [notice, setNotice] = useState("");

  const city = getCity(cityId)!;
  // The user's own data lives in this browser only, so it is read after mount.
  useEffect(() => {
    setData(loadCityData(cityId));
  }, [cityId]);
  const model = useMemo(() => getCityModel(city, data), [city, data]);
  const status = dataStatus(model);
  const lineApi = useLineScenario(model, mode, initialScenario);
  const { line, network } = lineApi;
  const incidents = useMemo(() => detectIncidents(model), [model]);
  const covered = useMemo(() => existingCoverage(model), [model]);
  const scaleMax = useMemo(() => demandScaleMax(model), [model]);
  const cityNow = useMemo(() => model.cityHourly(model.thisWeek), [model]);
  const cityBase = useMemo(() => model.cityHourly(model.baselineMean), [model]);
  const n = model.grid.cells.length;

  const values = useMemo(() => {
    const v = new Float32Array(n);
    for (let c = 0; c < n; c++) v[c] = model.thisWeek[c * HOURS_PER_WEEK + hour];
    return v;
  }, [model, hour, n]);

  const site = useMemo(
    () => (pin ? scoreSite(model, pin, mode, covered, model.calibration) : null),
    [model, pin, mode, covered]
  );

  const changeData = useCallback(
    (next: CityData | null) => {
      if (next) saveCityData(next);
      else clearCityData(cityId);
      setData(next);
      setPin(null);
      setSuggestions([]);
    },
    [cityId]
  );

  // Reset per-city state when the city changes, and keep the URL shareable.
  useEffect(() => {
    // Compare with the last city rather than skipping the first run: React
    // strict mode runs mount effects twice, which would wipe a deep link.
    if (lastCity.current === cityId) return;
    lastCity.current = cityId;
    setSelected(null);
    setPin(null);
    setSuggestions([]);
    lineApi.clear();
  }, [cityId, lineApi]);

  // Keep the address bar on the current view, so copying it shares exactly this.
  const selectedIndex = selected ? incidents.findIndex((i) => i.id === selected.id) + 1 : 0;
  const lineCode = lineMode && line && line.stations.length > 0 ? encodeScenario(line) : undefined;
  const href = deskHref(cityId, tab, selectedIndex || undefined, suggestions.length > 0, lineCode);
  useEffect(() => {
    if (typeof window === "undefined" || !window.history?.replaceState) return;
    if (window.location.pathname + window.location.search !== href) window.history.replaceState(null, "", href);
  }, [href]);

  const lastMode = useRef(mode);
  useEffect(() => {
    if (lastMode.current !== mode) setSuggestions([]);
    lastMode.current = mode;
  }, [mode]);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setHour((h) => (h + 1) % HOURS_PER_WEEK), 180);
    return () => clearInterval(t);
  }, [playing]);

  const selectIncident = useCallback((i: Incident) => {
    setSelected((cur) => (cur?.id === i.id ? null : i));
    setPlaying(false);
    setHour(i.peakHour);
  }, []);

  const flash = useCallback((text: string) => {
    setNotice(text);
    setTimeout(() => setNotice((cur) => (cur === text ? "" : cur)), 2600);
  }, []);

  // Links that carried a line: say so when it could not be read or is not on this device.
  const openedRef = useRef(false);
  useEffect(() => {
    if (openedRef.current) return;
    openedRef.current = true;
    if (initialScenario === null) flash("That shared line could not be read");
    if (initialScenarioId && !lineApi.open(initialScenarioId)) flash("That saved line is not on this device");
  }, [initialScenario, initialScenarioId, lineApi, flash]);

  const copyLink = useCallback(() => {
    const url = window.location.origin + href;
    const clip = typeof navigator !== "undefined" ? navigator.clipboard : undefined;
    if (!clip?.writeText) {
      flash("Copy is not available here: use the address bar");
      return;
    }
    clip.writeText(url).then(
      () => flash("Link to this view copied"),
      () => flash("Copy failed: use the address bar")
    );
  }, [href, flash]);

  const exportCsv = useCallback(() => {
    downloadText(`metropulse-${cityId}-incidents.csv`, incidentsToCsv(incidents));
    flash(`${incidents.length} incident${incidents.length === 1 ? "" : "s"} saved as CSV`);
  }, [cityId, incidents, flash]);

  useDeskShortcuts(
    {
      togglePlay: () => setPlaying((p) => !p),
      step: (d) => {
        setPlaying(false);
        setHour((h) => (((h + d) % HOURS_PER_WEEK) + HOURS_PER_WEEK) % HOURS_PER_WEEK);
      },
      tab: (k) => setTab(TAB_ORDER[k]),
      incident: (dir) => {
        if (incidents.length === 0) return;
        const cur = selected ? incidents.findIndex((i) => i.id === selected.id) : -1;
        const next = cur < 0 ? (dir > 0 ? 0 : incidents.length - 1) : (cur + dir + incidents.length) % incidents.length;
        setTab("alerts");
        setSelected(incidents[next]);
        setPlaying(false);
        setHour(incidents[next].peakHour);
      },
      copyLink,
      exportCsv,
      openBriefing: () => window.location.assign(`/brief?city=${cityId}`),
      escape: () => {
        if (selected) setSelected(null);
        else if (lineMode && line) lineApi.clear();
        else if (pin) setPin(null);
        else setPlaying(false);
      },
      toggleHelp: () => setHelpOpen((o) => !o),
    },
    !helpOpen
  );

  const markers: Marker[] = useMemo(() => {
    const out: Marker[] = [];
    if (tab === "alerts")
      for (const i of incidents)
        out.push({ id: i.id, at: i.centroid, kind: "incident", label: i.headline });
    if (tab === "siting" && lineMode) {
      (line?.stations ?? []).forEach((s, k) =>
        out.push({ id: `st${k}`, at: model.grid.project(s.lat, s.lng), kind: "station", text: String(k + 1), label: `Station ${k + 1}` })
      );
    } else if (tab === "siting") {
      suggestions.forEach((s, k) =>
        out.push({ id: `pick${k}`, at: model.grid.cells[s.cell], kind: "pick", text: String(k + 1), label: `Suggested site ${k + 1}` })
      );
      if (pin) out.push({ id: "pin", at: pin, kind: "pin", label: "Your proposed site" });
    }
    return out;
  }, [tab, incidents, suggestions, pin, model, lineMode, line]);

  const linePoints = useMemo(() => (line ? line.stations.map((s) => model.grid.project(s.lat, s.lng)) : []), [line, model]);
  const stationNames = useMemo(
    () => (line ? line.stations.map((s, k) => s.name ?? placeName(model, linePoints[k])) : []),
    [line, linePoints, model]
  );
  const lineBands = useMemo(() => {
    if (!lineMode || !network) return { walk: undefined, feeder: undefined };
    const walk = new Set<number>();
    const feeder = new Set<number>();
    for (const s of network.stations) {
      s.walkCells.forEach((c) => walk.add(c));
      s.feederCells.forEach((c) => feeder.add(c));
    }
    return { walk, feeder };
  }, [lineMode, network]);

  const busiest = useMemo(() => {
    const order = Array.from({ length: n }, (_, i) => i).sort((a, b) => values[b] - values[a]);
    return order.slice(0, 5).map((c) => {
      const base = model.baselineMean[c * HOURS_PER_WEEK + hour];
      return {
        c,
        name: placeName(model, model.grid.cells[c]),
        v: values[c],
        trend: base > 0 ? values[c] / base - 1 : 0,
        day: cellDay(model.thisWeek, model.baselineMean, c, hour),
      };
    });
  }, [values, model, n, hour]);

  const delta = cityBase[hour] ? cityNow[hour] / cityBase[hour] - 1 : 0;

  return (
    <div className="paper-grain flex min-h-screen flex-col text-ink lg:h-screen">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b-2 border-ink px-4 py-2.5 sm:px-6">
        <Link href="/" className="focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <Wordmark />
        </Link>
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-2xl font-semibold leading-none">{city.name}</h1>
          <span className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">{city.state}</span>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span className="font-mono text-[11px] uppercase tracking-widest text-ink-soft">City</span>
          <select
            value={cityId}
            onChange={(e) => setCityId(e.target.value)}
            className="border border-ink bg-paper px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            {listCities().map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <nav role="tablist" aria-label="Desk" className="flex w-full border border-ink sm:ml-auto sm:w-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 px-3 py-1.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-signal sm:flex-none ${
                tab === t.id ? "bg-ink text-paper" : "hover:bg-paper-deep"
              }`}
            >
              <span className="mr-1.5 hidden font-mono text-[10px] uppercase tracking-widest opacity-60 sm:inline">{t.verb}</span>
              {t.label}
            </button>
          ))}
          <Link
            href={`/brief?city=${cityId}`}
            className="flex-1 border-l border-ink px-3 py-1.5 text-center text-sm font-medium sm:flex-none hover:bg-signal hover:text-paper focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-signal"
          >
            <span className="mr-1.5 hidden font-mono text-[10px] uppercase tracking-widest opacity-60 sm:inline">Persuade</span>
            Briefing
          </Link>
        </nav>
        <div className="no-print flex items-center gap-2">
          <button
            type="button"
            onClick={() => setDataOpen(true)}
            className={`border px-2.5 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
              data ? "border-supply bg-supply text-paper hover:bg-supply-deep" : "border-ink hover:bg-paper-deep"
            }`}
          >
            Your data
          </button>
          <button
            type="button"
            onClick={copyLink}
            className="border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            Copy link
          </button>
          <button
            type="button"
            onClick={() => setHelpOpen(true)}
            aria-label="Keyboard shortcuts"
            title="Keyboard shortcuts (?)"
            className="h-8 w-8 border border-ink font-mono text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            ?
          </button>
        </div>
      </header>
      <ShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
      <DataDrawer open={dataOpen} city={city} model={model} data={data} onChange={changeData} onClose={() => setDataOpen(false)} />
      <div role="status" aria-live="polite" className="sr-only">
        {notice}
      </div>
      {notice && (
        <div
          aria-hidden
          className="no-print pointer-events-none fixed bottom-24 left-1/2 z-40 -translate-x-1/2 border border-ink bg-ink px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-paper"
        >
          {notice}
        </div>
      )}

      {status ? (
        <p className="border-b border-ink/30 bg-supply/10 px-4 py-1 font-mono text-[11px] text-ink-soft sm:px-6">
          <span className="font-semibold text-supply-deep">Your data · </span>
          {status}. Demand between stations is still the sample model.
        </p>
      ) : (
        <p className="border-b border-ink/30 bg-signal/10 px-4 py-1 font-mono text-[11px] text-ink-soft sm:px-6">
          Sample city model: a seeded synthetic demand field built from {city.name}&rsquo;s real anchor points and published
          population, with scripted incidents. The algorithms are real; the numbers are illustrative until the city&rsquo;s own
          data is loaded under <strong>Your data</strong>.
        </p>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_380px]">
        <section className="relative min-h-[420px] border-ink lg:border-r-2">
          <HexMap
            title={`Hexagon map of ${city.name}`}
            grid={model.grid}
            anchors={city.anchors}
            values={values}
            scaleMax={scaleMax}
            outlined={tab === "alerts" && selected ? new Set(selected.cells) : undefined}
            walk={tab === "siting" ? (lineMode ? lineBands.walk : site ? new Set(site.walkCells) : undefined) : undefined}
            feeder={tab === "siting" ? (lineMode ? lineBands.feeder : site ? new Set(site.feederCells) : undefined) : undefined}
            markers={markers}
            hubs={data?.hubs ? model.hubs : undefined}
            line={tab === "siting" && lineMode ? linePoints : undefined}
            onPick={tab === "siting" ? (lineMode ? (p) => lineApi.addStation(p) : setPin) : undefined}
            className="absolute inset-0 h-full w-full"
          />
          <div className="pointer-events-none absolute bottom-3 left-3 border border-ink bg-paper/90 px-2 py-1.5">
            <div className="font-mono text-[10px] uppercase tracking-widest text-ink-soft">Trips per hexagon, this hour</div>
            <div className="mt-1 h-2 w-40" style={{ background: "linear-gradient(90deg,#EAE2D3,#F2B391 30%,#D9480F 65%,#6E2206)" }} />
            <div className="flex justify-between font-mono text-[10px] text-ink-faint">
              <span>0</span>
              <span>{fmtInt(scaleMax)}+</span>
            </div>
          </div>
        </section>

        <aside className="min-h-0 overflow-y-auto px-4 py-4 sm:px-5">
          {tab === "pulse" && (
            <div className="space-y-4">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">Trip ends, city-wide</div>
                <div className="font-display text-4xl font-bold leading-tight tabular">{fmtInt(cityNow[hour])}</div>
                <div className="text-sm text-ink-soft">
                  in the hour from {dayHourLabel(hour)},{" "}
                  <span className={delta >= 0 ? "text-signal-deep" : "text-supply"}>
                    {delta >= 0 ? "+" : ""}
                    {(delta * 100).toFixed(1)}%
                  </span>{" "}
                  against the four-week baseline
                </div>
              </div>
              <div>
                <h2 className="rule-double pt-2 font-display text-lg font-semibold">Busiest hexagons now</h2>
                <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                  Today&rsquo;s 24 hours · trips this hour · against baseline
                </p>
                <ol className="mt-1 divide-y divide-ink/15">
                  {busiest.map((b, k) => (
                    <li key={b.c} className="flex items-center gap-3 py-1.5 text-sm">
                      <span className="w-4 font-mono text-ink-faint">{k + 1}</span>
                      <span className="min-w-0 flex-1 leading-snug">{b.name}</span>
                      <Sparkline
                        now={b.day.now}
                        base={b.day.base}
                        at={b.day.at}
                        width={56}
                        label={`${b.name}: today's 24 hours against the baseline`}
                      />
                      <span className="w-[62px] shrink-0 text-right leading-tight">
                        <span className="block font-mono tabular">{fmtInt(b.v)}</span>
                        <span
                          className={`block font-mono text-[10px] tabular ${b.trend >= 0 ? "text-signal-deep" : "text-supply"}`}
                          title="Against the same hour in the four-week baseline"
                        >
                          {b.trend >= 0 ? "▲" : "▼"} {Math.abs(b.trend * 100).toFixed(0)}%
                        </span>
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
              <dl className="grid grid-cols-3 gap-2 border-t border-ink/20 pt-2 text-center">
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">Hexagons</dt>
                  <dd className="font-display text-xl">{fmtInt(n)}</dd>
                </div>
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">Each</dt>
                  <dd className="font-display text-xl">{model.grid.cellAreaKm2.toFixed(2)} km²</dd>
                </div>
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">Residents</dt>
                  <dd className="font-display text-xl">{(city.population / 1e6).toFixed(1)}M</dd>
                </div>
              </dl>
              <p className="text-xs leading-relaxed text-ink-soft">
                Press play to watch the week: the weekday morning wave into the job hubs, the evening release, the quieter
                weekend. Diamonds on the timeline are this week&rsquo;s incidents. Press{" "}
                <kbd className="border border-ink/50 px-1 font-mono text-[10px]">?</kbd> for keyboard shortcuts.
              </p>
            </div>
          )}
          {tab === "alerts" && (
            <div className="space-y-3">
              <div>
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="font-display text-lg font-semibold">This week&rsquo;s incidents</h2>
                  <button
                    type="button"
                    onClick={exportCsv}
                    className="no-print shrink-0 border border-ink px-2 py-0.5 font-mono text-[11px] uppercase tracking-widest hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
                  >
                    Download CSV
                  </button>
                </div>
                <p className="text-xs text-ink-soft">
                  Each hex-hour is compared with the same hour in the four previous weeks (median and MAD). Flagged hex-hours that
                  touch in space or time become one incident, explained by a fixed rule trace.
                </p>
              </div>
              <AlertFeed incidents={incidents} selectedId={selected?.id ?? null} onSelect={selectIncident} />
            </div>
          )}
          {tab === "siting" && (
            <SitingPanel
              mode={mode}
              onMode={setMode}
              result={site}
              placeName={pin ? placeName(model, pin) : null}
              suggestions={suggestions}
              suggestionNames={suggestions.map((s) => placeName(model, model.grid.cells[s.cell]))}
              onSuggest={() => {
                const picks = suggestSites(model, mode, 3, covered, model.calibration);
                if (lineMode) lineApi.replace(scenarioFromSuggestions(model, mode, picks));
                else setSuggestions(picks);
              }}
              onPickSuggestion={(k) => {
                const c = model.grid.cells[suggestions[k].cell];
                setPin({ x: c.x, y: c.y });
              }}
              onClear={() => setPin(null)}
              lineMode={lineMode}
              onLineMode={setLineMode}
              line={line}
              network={network}
              stationNames={stationNames}
              scenarios={lineApi.scenarios}
              onRemoveStation={lineApi.removeStation}
              onMoveStation={lineApi.moveStation}
              onAlignment={lineApi.setAlignment}
              onCosts={lineApi.setCosts}
              onRename={lineApi.rename}
              onSave={() => {
                lineApi.save();
                flash("Line saved on this device");
              }}
              onCopyLink={copyLink}
              onClearLine={lineApi.clear}
              onOpenScenario={(id) => {
                if (lineApi.open(id)) setLineMode(true);
              }}
              onDeleteScenario={lineApi.remove}
              compareHref={lineCode ? `/compare?city=${cityId}&a=${encodeURIComponent(lineCode)}` : null}
            />
          )}
        </aside>
      </div>

      <footer className="border-t-2 border-ink px-4 py-3 sm:px-6">
        <Timeline
          hour={hour}
          onHour={(h) => {
            setPlaying(false);
            setHour(h);
          }}
          playing={playing}
          onPlaying={setPlaying}
          current={cityNow}
          baseline={cityBase}
          pins={incidents.map((i) => ({ hour: i.peakHour, kind: i.kind, label: i.headline }))}
        />
      </footer>
    </div>
  );
}

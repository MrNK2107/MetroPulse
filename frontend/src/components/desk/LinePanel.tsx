"use client";

import Link from "next/link";
import { ALIGNMENTS, Alignment, COST_SOURCE, CostTable, DEFAULT_COSTS, NetworkResult, Scenario } from "@/lib/pulse/scenario";
import { fmtInt } from "./SitingPanel";

export interface LinePanelProps {
  line: Scenario | null;
  network: NetworkResult | null;
  /** Display name per station, aligned with `line.stations`. */
  stationNames: string[];
  scenarios: Scenario[];
  onRemoveStation: (k: number) => void;
  onMoveStation: (k: number, dir: -1 | 1) => void;
  onAlignment: (a: Alignment) => void;
  onCosts: (c: CostTable) => void;
  onRename: (name: string) => void;
  onSave: () => void;
  onCopyLink: () => void;
  onClearLine: () => void;
  onSuggest: () => void;
  onOpenScenario: (id: string) => void;
  onDeleteScenario: (id: string) => void;
  compareHref: string | null;
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-t border-ink/20 pt-1.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">{label}</div>
      <div className="font-display text-xl leading-tight tabular">{value}</div>
      {hint && <div className="text-xs text-ink-soft">{hint}</div>}
    </div>
  );
}

const pct = (x: number) => `${(x * 100).toFixed(x * 100 < 10 ? 1 : 0)}%`;
const btn =
  "border border-ink px-2.5 py-1 text-sm hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal disabled:opacity-40";
const tiny = "font-mono text-[10px] uppercase tracking-widest underline decoration-ink/30 underline-offset-2 hover:decoration-ink";

export function LinePanel(p: LinePanelProps) {
  const { line, network } = p;
  const costs = line?.costs ?? DEFAULT_COSTS;
  const align = line?.alignment ?? "elevated";

  const setCost = (which: keyof CostTable, value: string) => {
    const v = Number(value);
    if (!Number.isFinite(v) || v < 0) return;
    p.onCosts({ ...costs, [which]: { ...costs[which], [align]: v } });
  };

  return (
    <div className="space-y-4">
      {!line || !network ? (
        <p className="border border-dashed border-ink/40 p-3 text-sm text-ink-soft">
          Click the map to add stations in order. Each station is scored net of the existing hubs and the stations before it,
          so the line&rsquo;s boardings are its own, not double-counted.
        </p>
      ) : (
        <section aria-label="Proposed line" className="space-y-3">
          <div className="flex items-end justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
                Proposed line · {line.stations.length} station{line.stations.length === 1 ? "" : "s"}
              </div>
              <label className="block">
                <span className="sr-only">Line name</span>
                <input
                  value={line.name}
                  onChange={(e) => p.onRename(e.target.value)}
                  className="w-full border-b border-ink/40 bg-transparent font-display text-xl font-semibold leading-tight focus:border-ink focus:outline-none"
                />
              </label>
            </div>
            <div className="text-right">
              <div className="font-display text-5xl font-bold leading-none text-supply tabular">{network.score}</div>
              <div className="whitespace-nowrap font-mono text-[10px] uppercase tracking-widest text-ink-faint">score / 100</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Daily boardings" value={fmtInt(network.boardings)} hint={`${pct(network.newShare)} new coverage`} />
            <Stat label="Walk-band coverage" value={`${pct(network.coverageNow)} → ${pct(network.coverageAfter)}`} hint="residents within a walk band" />
            <Stat label="Residents · jobs in walk bands" value={`${fmtInt(network.residents)} · ${fmtInt(network.jobs)}`} />
            <Stat label="Line length" value={`${network.lengthKm.toFixed(1)} km`} hint={`spacing in band ${pct(network.spacingCompliance)}`} />
            <Stat label="Capital cost" value={`₹${fmtInt(network.costCr)} cr`} hint="sketch, see assumptions" />
            <Stat label="Cost per daily boarding" value={`₹${network.costPerBoardingLakh.toFixed(2)} lakh`} />
          </div>

          <ol aria-label="Stations on the line" className="divide-y divide-ink/15 border-t border-ink/20">
            {network.stations.map((s, k) => (
              <li key={k} className="flex items-start gap-2 py-1.5 text-sm">
                <span className="w-5 shrink-0 font-display text-lg font-bold text-supply">{k + 1}</span>
                <div className="min-w-0 flex-1">
                  <div className="font-medium leading-snug">{p.stationNames[k] ?? s.name}</div>
                  <div className="font-mono text-[11px] text-ink-soft">
                    {fmtInt(s.dailyBoardings)} boardings/day · {Math.round(s.newShare * 100)}% new
                    {s.spacingKmToNext !== undefined && ` · ${s.spacingKmToNext.toFixed(1)} km to next`}
                  </div>
                  {s.spacingWarning && <div className="text-xs text-signal-deep">{s.spacingWarning}</div>}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-0.5">
                  <button type="button" aria-label={`Move up station ${k + 1}`} disabled={k === 0} onClick={() => p.onMoveStation(k, -1)} className={tiny}>
                    Up
                  </button>
                  <button
                    type="button"
                    aria-label={`Move down station ${k + 1}`}
                    disabled={k === network.stations.length - 1}
                    onClick={() => p.onMoveStation(k, 1)}
                    className={tiny}
                  >
                    Down
                  </button>
                  <button type="button" aria-label={`Remove station ${k + 1}`} onClick={() => p.onRemoveStation(k)} className={`${tiny} text-signal-deep`}>
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ol>

          <div className="space-y-2 border-t border-ink/20 pt-2">
            <label className="flex items-center justify-between gap-2 text-sm">
              <span className="font-mono text-[10px] uppercase tracking-widest text-ink-soft">Alignment</span>
              <select value={align} onChange={(e) => p.onAlignment(e.target.value as Alignment)} className="border border-ink bg-paper px-2 py-0.5 text-sm">
                {ALIGNMENTS.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="text-sm">
                <span className="block font-mono text-[10px] uppercase tracking-widest text-ink-soft">₹ cr per km</span>
                <input
                  type="number"
                  min={0}
                  value={costs.perKmCr[align]}
                  onChange={(e) => setCost("perKmCr", e.target.value)}
                  className="w-full border border-ink bg-paper px-2 py-0.5 tabular"
                />
              </label>
              <label className="text-sm">
                <span className="block font-mono text-[10px] uppercase tracking-widest text-ink-soft">₹ cr per station</span>
                <input
                  type="number"
                  min={0}
                  value={costs.perStationCr[align]}
                  onChange={(e) => setCost("perStationCr", e.target.value)}
                  className="w-full border border-ink bg-paper px-2 py-0.5 tabular"
                />
              </label>
            </div>
            <p className="text-[11px] leading-snug text-ink-soft">Assumptions: {COST_SOURCE}</p>
          </div>

          <p className="bg-paper-deep px-2 py-1.5 font-mono text-[11px] leading-relaxed">{network.formula}</p>
          <p className="bg-paper-deep px-2 py-1.5 font-mono text-[11px] leading-relaxed">{network.costFormula}</p>

          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={p.onSave} className={`${btn} bg-ink text-paper hover:bg-supply`}>
              Save line
            </button>
            <button type="button" onClick={p.onCopyLink} className={btn}>
              Copy link
            </button>
            {p.compareHref && (
              <Link href={p.compareHref} className={btn}>
                Compare
              </Link>
            )}
            <button type="button" onClick={p.onClearLine} className="text-sm underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
              Clear line
            </button>
          </div>
        </section>
      )}

      <div className="rule-double pt-3">
        <button
          type="button"
          onClick={p.onSuggest}
          className="w-full border-2 border-ink bg-ink px-3 py-2 text-sm font-semibold text-paper transition hover:border-supply hover:bg-supply focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
        >
          Suggest a line
        </button>
        <p className="mt-1 text-xs text-ink-soft">
          Three greedy picks loaded as a line. Each pick counts only demand the earlier picks and existing hubs do not already serve.
        </p>
      </div>

      <div className="border-t border-ink/20 pt-2">
        <h3 className="font-display text-lg font-semibold">Saved lines</h3>
        {p.scenarios.length === 0 ? (
          <p className="text-xs text-ink-soft">Nothing saved on this device yet. Saved lines stay in this browser.</p>
        ) : (
          <ol aria-label="Saved lines" className="divide-y divide-ink/15">
            {p.scenarios.map((s) => (
              <li key={s.id} className="flex items-center gap-2 py-1.5 text-sm">
                <button type="button" aria-label={`Open ${s.name}`} onClick={() => p.onOpenScenario(s.id)} className="min-w-0 flex-1 text-left hover:text-supply">
                  <span className="block truncate font-medium">{s.name}</span>
                  <span className="font-mono text-[11px] text-ink-soft">
                    {s.stations.length} station{s.stations.length === 1 ? "" : "s"} · {s.mode} · {s.updatedAt.slice(0, 10)}
                  </span>
                </button>
                <button type="button" aria-label={`Delete ${s.name}`} onClick={() => p.onDeleteScenario(s.id)} className={`${tiny} text-signal-deep`}>
                  Delete
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

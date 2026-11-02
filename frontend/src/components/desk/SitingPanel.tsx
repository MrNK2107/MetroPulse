"use client";

import { hourLabel } from "@/lib/pulse/model";
import { MODES, ModeId, SiteResult, Suggestion } from "@/lib/pulse/siting";

interface Props {
  mode: ModeId;
  onMode: (m: ModeId) => void;
  result: SiteResult | null;
  placeName: string | null;
  suggestions: Suggestion[];
  suggestionNames: string[];
  onSuggest: () => void;
  /** Pin suggestion k (0-based) so its full score and catchment show. */
  onPickSuggestion?: (k: number) => void;
  onClear: () => void;
}

export const fmtInt = (n: number) => Math.round(n).toLocaleString("en-IN");

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-t border-ink/20 pt-1.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">{label}</div>
      <div className="font-display text-2xl leading-tight tabular">{value}</div>
      {hint && <div className="text-xs text-ink-soft">{hint}</div>}
    </div>
  );
}

export function SitingPanel({ mode, onMode, result, placeName, suggestions, suggestionNames, onSuggest, onPickSuggestion, onClear }: Props) {
  const m = MODES[mode];
  const maxHourly = result ? Math.max(...result.hourly) : 1;
  return (
    <div className="space-y-4">
      <div role="radiogroup" aria-label="Mode" className="grid grid-cols-3 border border-ink">
        {(Object.keys(MODES) as ModeId[]).map((id) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={id === mode}
            onClick={() => onMode(id)}
            className={`px-2 py-1.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-signal ${
              id === mode ? "bg-supply text-paper" : "hover:bg-paper-deep"
            }`}
          >
            {MODES[id].label.split(" ")[0]}
          </button>
        ))}
      </div>
      <p className="font-mono text-[11px] uppercase tracking-wider text-ink-soft">
        Walk band {m.walkKm * 1000} m · feeder band {m.feederKm} km
      </p>

      {!result && (
        <p className="border border-dashed border-ink/40 p-3 text-sm text-ink-soft">
          Click the map to drop a pin. MetroPulse draws the walk and feeder catchments and scores the site.
        </p>
      )}

      {result && (
        <section aria-label="Site score" className="space-y-3">
          <div className="flex items-end justify-between gap-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">{m.label} near</div>
              <div className="font-display text-xl font-semibold leading-tight">{placeName}</div>
            </div>
            <div className="text-right">
              <div className="font-display text-5xl font-bold leading-none text-supply tabular">{result.score}</div>
              <div className="whitespace-nowrap font-mono text-[10px] uppercase tracking-widest text-ink-faint">score / 100</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Est. daily boardings" value={fmtInt(result.dailyBoardings)} />
            <Stat label="New coverage" value={`${Math.round(result.newShare * 100)}%`} hint="not already served by a hub" />
            <Stat label="Residents in walk band" value={fmtInt(result.residents)} />
            <Stat label="Jobs in walk band" value={fmtInt(result.jobs)} />
          </div>
          <div>
            <div className="mb-1 flex justify-between font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
              <span>Weekday boardings by hour</span>
              <span>peak {hourLabel(result.peakHour)}</span>
            </div>
            <div className="flex h-14 items-end gap-px" aria-hidden>
              {result.hourly.map((v, h) => (
                <div
                  key={h}
                  className={h === result.peakHour ? "flex-1 bg-supply" : "flex-1 bg-supply-soft"}
                  style={{ height: `${(v / maxHourly) * 100}%` }}
                />
              ))}
            </div>
          </div>
          <p className="bg-paper-deep px-2 py-1.5 font-mono text-[11px] leading-relaxed">{result.formula}</p>
          <button type="button" onClick={onClear} className="text-sm underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
            Clear pin
          </button>
        </section>
      )}

      <div className="rule-double pt-3">
        <button
          type="button"
          onClick={onSuggest}
          className="w-full border-2 border-ink bg-ink px-3 py-2 text-sm font-semibold text-paper transition hover:bg-supply hover:border-supply focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
        >
          Suggest 3 sites
        </button>
        <p className="mt-1 text-xs text-ink-soft">
          Greedy search over every hexagon. Each pick counts only demand the earlier picks and existing hubs do not already serve.
        </p>
        {suggestions.length > 0 && (
          <ol className="mt-3 space-y-2">
            {suggestions.map((s, k) => (
              <li
                key={s.cell}
                aria-label={`Suggested site ${k + 1}: ${suggestionNames[k]}`}
                className="flex items-baseline gap-3 border-t border-ink/20 pt-2"
              >
                <span className="font-display text-2xl font-bold text-supply">{k + 1}</span>
                <button
                  type="button"
                  onClick={() => onPickSuggestion?.(k)}
                  className="flex-1 text-left hover:text-supply focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
                >
                  <span className="block font-medium underline decoration-ink/20 underline-offset-2">{suggestionNames[k]}</span>
                  <span className="font-mono text-[11px] text-ink-soft">
                    {fmtInt(s.result.newBoardings)} new boardings/day · score {s.result.score}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

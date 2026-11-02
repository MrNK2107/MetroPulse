"use client";

import type { Incident } from "@/lib/pulse/alerts";

interface Props {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (i: Incident) => void;
}

export function AlertFeed({ incidents, selectedId, onSelect }: Props) {
  if (incidents.length === 0) {
    return <p className="text-sm text-ink-soft">No incidents this week. Every hex-hour stayed inside its baseline band.</p>;
  }
  return (
    <ul aria-label="Incidents" className="space-y-3">
      {incidents.map((i, k) => {
        const open = i.id === selectedId;
        return (
          <li
            key={i.id}
            className={`feed-enter border-l-4 bg-paper/80 ${i.kind === "surge" ? "border-signal" : "border-supply"} ${
              open ? "shadow-[4px_4px_0_0_#16130F] ring-1 ring-ink" : "ring-1 ring-paper-edge"
            }`}
            style={{ animationDelay: `${k * 60}ms` }}
          >
            <button
              type="button"
              onClick={() => onSelect(i)}
              aria-expanded={open}
              className="block w-full px-3 py-2 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
            >
              <span className="block font-display text-[17px] font-semibold leading-snug">{i.headline}</span>
              <span className="mt-0.5 block font-mono text-[11px] uppercase tracking-wider text-ink-faint">
                {i.kind} · {i.cells.length} hexagons · {i.hexHours} hex-hours
              </span>
            </button>
            {open && (
              <div className="space-y-2 px-3 pb-3 text-sm leading-relaxed">
                <p>{i.explanation}</p>
                <p>
                  <span className="font-semibold">Likely cause: </span>
                  {i.likelyCause}
                </p>
                <p>
                  <span className="font-semibold">What to check: </span>
                  {i.whatToCheck}
                </p>
                <details className="group">
                  <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-wider text-ink-soft hover:text-ink">
                    Rule trace
                  </summary>
                  <ol className="mt-1 list-decimal space-y-0.5 pl-5 font-mono text-[11px] text-ink-soft">
                    {i.ruleTrace.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ol>
                </details>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

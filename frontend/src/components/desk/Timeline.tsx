"use client";

import { useMemo } from "react";
import { DAYS, dayHourLabel } from "@/lib/pulse/model";

export interface TimelinePin {
  hour: number;
  kind: "surge" | "drop";
  label: string;
}

interface Props {
  hour: number;
  onHour: (h: number) => void;
  playing: boolean;
  onPlaying: (p: boolean) => void;
  current: number[];
  baseline: number[];
  pins: TimelinePin[];
}

const W = 1000;
const H = 72;

export function Timeline({ hour, onHour, playing, onPlaying, current, baseline, pins }: Props) {
  const { area, line } = useMemo(() => {
    const max = Math.max(...current, ...baseline) || 1;
    const x = (h: number) => (h / 167) * W;
    const y = (v: number) => H - (v / max) * (H - 6);
    const area =
      `M0,${H} ` + current.map((v, h) => `L${x(h).toFixed(1)},${y(v).toFixed(1)}`).join(" ") + ` L${W},${H} Z`;
    const line = baseline.map((v, h) => `${h ? "L" : "M"}${x(h).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    return { area, line };
  }, [current, baseline]);

  const cursor = (hour / 167) * 100;

  return (
    <div className="flex items-stretch gap-4">
      <button
        type="button"
        onClick={() => onPlaying(!playing)}
        aria-label={playing ? "Pause playback" : "Play the week"}
        aria-pressed={playing}
        className="flex h-12 w-12 shrink-0 items-center justify-center self-center rounded-full border-2 border-ink bg-ink text-paper transition hover:bg-signal hover:border-signal focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
      >
        {playing ? (
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <rect x="2" y="1" width="3.5" height="12" fill="currentColor" />
            <rect x="8.5" y="1" width="3.5" height="12" fill="currentColor" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <path d="M3 1 L13 7 L3 13 Z" fill="currentColor" />
          </svg>
        )}
      </button>
      <div className="w-28 shrink-0 self-center">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">This week</div>
        <div className="font-display text-2xl leading-none tabular" aria-live="off">
          {dayHourLabel(hour)}
        </div>
      </div>
      <div className="relative min-w-0 flex-1">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="block h-[72px] w-full" aria-hidden>
          {DAYS.map((d, i) => (
            <g key={d}>
              <rect x={(i * 24 * W) / 167} y={0} width={(24 * W) / 167} height={H} fill={i >= 5 ? "#EAE2D3" : "transparent"} />
              <line x1={(i * 24 * W) / 167} x2={(i * 24 * W) / 167} y1={0} y2={H} stroke="#D8CDB8" strokeWidth={1} />
            </g>
          ))}
          <path d={area} fill="#D9480F" fillOpacity={0.22} stroke="#D9480F" strokeWidth={1.4} vectorEffect="non-scaling-stroke" />
          <path d={line} fill="none" stroke="#16130F" strokeWidth={1} strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="pointer-events-none absolute inset-y-0 w-px bg-ink" style={{ left: `${cursor}%` }} />
        {pins.map((p) => (
          <button
            key={`${p.kind}-${p.hour}-${p.label}`}
            type="button"
            onClick={() => onHour(p.hour)}
            aria-label={p.label}
            title={p.label}
            className={`absolute -top-2 z-10 h-4 w-4 -translate-x-1/2 rotate-45 border border-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-ink ${
              p.kind === "surge" ? "bg-signal" : "bg-supply"
            }`}
            style={{ left: `${(p.hour / 167) * 100}%` }}
          />
        ))}
        {/* On a phone the strip is ~180px wide: three-letter labels would push the page sideways. */}
        <div className="mt-1 flex font-mono text-[10px] uppercase tracking-normal text-ink-faint sm:tracking-widest">
          {DAYS.map((d) => (
            <span key={d} className="min-w-0 flex-1">
              <span className="sm:hidden" aria-hidden>
                {d[0]}
              </span>
              <span className="hidden sm:inline">{d}</span>
            </span>
          ))}
        </div>
        <input
          type="range"
          min={0}
          max={167}
          step={1}
          value={hour}
          onChange={(e) => onHour(Number(e.target.value))}
          aria-label="Hour of the week"
          aria-valuetext={dayHourLabel(hour)}
          className="absolute inset-x-0 top-0 h-[72px] w-full cursor-ew-resize opacity-0"
        />
      </div>
    </div>
  );
}

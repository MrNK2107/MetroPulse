"use client";

import { memo, useMemo, useRef } from "react";
import type { HexGrid, Point, Anchor } from "@/lib/pulse/geo";

export interface Marker {
  id: string;
  at: Point;
  label: string;
  kind: "pin" | "pick" | "incident";
  text?: string;
}

interface Props {
  title: string;
  grid: HexGrid;
  anchors: Anchor[];
  values: ArrayLike<number>;
  scaleMax: number;
  outlined?: Set<number>;
  walk?: Set<number>;
  feeder?: Set<number>;
  markers?: Marker[];
  onPick?: (p: Point) => void;
  className?: string;
}

const STOPS: [number, [number, number, number]][] = [
  [0, [234, 226, 211]],
  [0.3, [242, 179, 145]],
  [0.65, [217, 72, 15]],
  [1, [110, 34, 6]],
];

export function demandColour(t: number): string {
  const v = Math.max(0, Math.min(1, t));
  for (let i = 1; i < STOPS.length; i++) {
    const [t1, c1] = STOPS[i];
    const [t0, c0] = STOPS[i - 1];
    if (v <= t1) {
      const k = (v - t0) / (t1 - t0);
      const c = c0.map((x, j) => Math.round(x + (c1[j] - x) * k));
      return `rgb(${c[0]},${c[1]},${c[2]})`;
    }
  }
  return "rgb(110,34,6)";
}

const HexLayer = memo(function HexLayer({
  paths,
  values,
  scaleMax,
}: {
  paths: string[];
  values: ArrayLike<number>;
  scaleMax: number;
}) {
  return (
    <g>
      {paths.map((d, i) => (
        <path key={i} d={d} fill={demandColour(Math.sqrt(values[i] / scaleMax))} stroke="#F4EFE6" strokeWidth={0.04} />
      ))}
    </g>
  );
});

function HexMapInner({
  title,
  grid,
  anchors,
  values,
  scaleMax,
  outlined,
  walk,
  feeder,
  markers = [],
  onPick,
  className,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);

  const { paths, viewBox, boundary, size } = useMemo(() => {
    const paths = grid.cells.map((c) => {
      const pts = grid.corners(c);
      return "M" + pts.map((p) => `${p.x.toFixed(3)},${(-p.y).toFixed(3)}`).join("L") + "Z";
    });
    const xs = grid.boundary.map((p) => p.x);
    const ys = grid.boundary.map((p) => -p.y);
    const pad = 1.5;
    const minX = Math.min(...xs) - pad;
    const minY = Math.min(...ys) - pad;
    const w = Math.max(...xs) - Math.min(...xs) + 2 * pad;
    const h = Math.max(...ys) - Math.min(...ys) + 2 * pad;
    const boundary = "M" + grid.boundary.map((p) => `${p.x.toFixed(3)},${(-p.y).toFixed(3)}`).join("L") + "Z";
    return { paths, viewBox: `${minX} ${minY} ${w} ${h}`, boundary, size: Math.max(w, h) };
  }, [grid]);

  const fs = size / 70; // label font size in km units

  const hubs = useMemo(
    // Some configured anchors sit well outside the sample boundary; drawing them
    // leaves an orphan label in the margin, so keep only those near a hexagon.
    () =>
      anchors
        .map((a) => ({ a, p: grid.project(a.lat, a.lng) }))
        .filter(({ p }) => grid.within(p.x, p.y, 1.5).length > 0),
    [anchors, grid]
  );

  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!onPick) return;
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM?.();
    if (!svg || !ctm || typeof svg.createSVGPoint !== "function") {
      onPick({ x: 0, y: 0 });
      return;
    }
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const p = pt.matrixTransform(ctm.inverse());
    // A pin off the hexagons would score an empty catchment; ignore it.
    if (grid.cellAt(p.x, -p.y) === undefined) return;
    onPick({ x: p.x, y: -p.y });
  };

  const labelX = (p: { x: number; y: number }) => {
    let x = p.x + fs * 0.6;
    for (const m of markers) {
      if (Math.abs(m.at.y - p.y) < fs * 1.4 && m.at.x > p.x - fs * 1.4 && m.at.x < x + fs * 1.2) x = m.at.x + fs * 1.5;
    }
    return x;
  };

  return (
    <svg
      ref={svgRef}
      role="img"
      aria-label={title}
      viewBox={viewBox}
      preserveAspectRatio="xMidYMid meet"
      className={className}
      onClick={handleClick}
      style={{ cursor: onPick ? "crosshair" : "default" }}
    >
      <path d={boundary} fill="#EAE2D3" stroke="#16130F" strokeWidth={0.12} strokeDasharray="0.5 0.3" />
      {/* Fade demand behind a catchment so the walk and feeder bands read clearly. */}
      <g opacity={walk || feeder ? 0.55 : 1}>
        <HexLayer paths={paths} values={values} scaleMax={scaleMax} />
      </g>
      {feeder && (
        <g>
          {Array.from(feeder).map((i) => (
            <path key={`f${i}`} d={paths[i]} fill="#1E3A8A" fillOpacity={0.2} stroke="#1E3A8A" strokeOpacity={0.35} strokeWidth={0.03} />
          ))}
        </g>
      )}
      {walk && (
        <g>
          {Array.from(walk).map((i) => (
            <path key={`w${i}`} d={paths[i]} fill="#1E3A8A" fillOpacity={0.6} stroke="#F4EFE6" strokeWidth={0.05} />
          ))}
        </g>
      )}
      {outlined && (
        <g>
          {Array.from(outlined).map((i) => (
            <path key={`o${i}`} d={paths[i]} fill="none" stroke="#16130F" strokeWidth={0.14} />
          ))}
        </g>
      )}
      <g>
        {hubs.map(({ a, p }) =>
          a.type === "transport" ? (
            <rect
              key={a.name}
              x={p.x - fs * 0.35}
              y={-p.y - fs * 0.35}
              width={fs * 0.7}
              height={fs * 0.7}
              fill="#F4EFE6"
              stroke="#1E3A8A"
              strokeWidth={fs * 0.18}
            >
              <title>{`${a.name} (existing hub)`}</title>
            </rect>
          ) : (
            <circle key={a.name} cx={p.x} cy={-p.y} r={fs * 0.22} fill="#16130F">
              <title>{a.name}</title>
            </circle>
          )
        )}
      </g>
      <g>
        {markers.map((m) =>
          m.kind === "pin" ? (
            <g key={m.id} transform={`translate(${m.at.x},${-m.at.y})`}>
              <circle r={fs * 0.9} fill="#1E3A8A" stroke="#F4EFE6" strokeWidth={fs * 0.25} />
              <circle r={fs * 0.3} fill="#F4EFE6" />
              <title>{m.label}</title>
            </g>
          ) : m.kind === "pick" ? (
            <g key={m.id} transform={`translate(${m.at.x},${-m.at.y})`}>
              <circle r={fs * 1.1} fill="#F4EFE6" stroke="#1E3A8A" strokeWidth={fs * 0.3} />
              <text
                textAnchor="middle"
                dy={fs * 0.42}
                fontSize={fs * 1.2}
                fontFamily="var(--font-display), serif"
                fontWeight={700}
                fill="#1E3A8A"
              >
                {m.text}
              </text>
              <title>{m.label}</title>
            </g>
          ) : (
            <g key={m.id} transform={`translate(${m.at.x},${-m.at.y})`}>
              <path
                d={`M0,${-fs * 1.3} L${fs * 1.1},${fs * 0.7} L${-fs * 1.1},${fs * 0.7}Z`}
                fill="#D9480F"
                stroke="#16130F"
                strokeWidth={fs * 0.15}
              />
              <text textAnchor="middle" dy={fs * 0.45} fontSize={fs * 0.9} fontWeight={700} fill="#F4EFE6">
                !
              </text>
              <title>{m.label}</title>
            </g>
          )
        )}
      </g>
      {/* Labels sit above the markers and step right of any marker that would cover them. */}
      <g>
        {hubs.map(({ a, p }) => (
          <text
            key={`t${a.name}`}
            x={labelX(p)}
            y={-p.y + fs * 0.35}
            fontSize={fs}
            fontFamily="var(--font-mono), monospace"
            fill="#16130F"
            stroke="#F4EFE6"
            strokeWidth={fs * 0.16}
            paintOrder="stroke"
            style={{ pointerEvents: "none" }}
          >
            {a.name}
          </text>
        ))}
      </g>
    </svg>
  );
}

export const HexMap = memo(HexMapInner);

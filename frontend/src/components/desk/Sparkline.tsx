interface Props {
  now: number[];
  base: number[];
  /** Index of the current point, drawn as a dot. */
  at: number;
  label: string;
  width?: number;
  height?: number;
}

/** A 24-hour trace for one hexagon: this week (signal) over the four-week baseline (dashed ink). */
export function Sparkline({ now, base, at, label, width = 72, height = 18 }: Props) {
  const max = Math.max(1, ...now, ...base);
  const last = Math.max(1, now.length - 1);
  const x = (i: number) => (i / last) * width;
  const y = (v: number) => height - 1 - (v / max) * (height - 2);
  const path = (vs: number[]) => vs.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label} className="shrink-0">
      <path d={path(base)} fill="none" stroke="#16130F" strokeOpacity={0.45} strokeWidth={1} strokeDasharray="2 2" />
      <path d={path(now)} fill="none" stroke="#D9480F" strokeWidth={1.4} />
      {now[at] !== undefined && <circle cx={x(at)} cy={y(now[at])} r={2} fill="#16130F" />}
    </svg>
  );
}

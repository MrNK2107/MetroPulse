"use client";

import { useEffect, useMemo, useState } from "react";
import { getCity } from "@/lib/pulse/geo";
import { demandScaleMax, getCityModel, HOURS_PER_WEEK, dayHourLabel } from "@/lib/pulse/model";
import { HexMap } from "@/components/desk/HexMap";

/** The landing page's live map: Chennai's sample week, playing slowly. */
export function HeroMap() {
  const city = getCity("chennai")!;
  const model = useMemo(() => getCityModel(city), [city]);
  const [hour, setHour] = useState(24 + 8);

  useEffect(() => {
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const t = setInterval(() => setHour((h) => (h + 1) % HOURS_PER_WEEK), 700);
    return () => clearInterval(t);
  }, []);

  const n = model.grid.cells.length;
  const values = useMemo(() => {
    const v = new Float32Array(n);
    for (let c = 0; c < n; c++) v[c] = model.thisWeek[c * HOURS_PER_WEEK + hour];
    return v;
  }, [model, hour, n]);
  const scaleMax = useMemo(() => demandScaleMax(model), [model]);

  return (
    <div className="relative h-full w-full">
      <HexMap
        title="Chennai's sample week, hour by hour"
        grid={model.grid}
        anchors={city.anchors}
        values={values}
        scaleMax={scaleMax}
        className="h-full w-full"
      />
      <div className="absolute right-2 top-2 border border-ink bg-paper px-2 py-1 text-right">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Chennai · sample week</div>
        <div className="font-display text-xl leading-none tabular">{dayHourLabel(hour)}</div>
      </div>
    </div>
  );
}

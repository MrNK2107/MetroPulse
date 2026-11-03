"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Point } from "@/lib/pulse/geo";
import type { CityModel } from "@/lib/pulse/model";
import type { ModeId } from "@/lib/pulse/siting";
import { Alignment, CostTable, evaluateScenario, newScenarioId, Scenario } from "@/lib/pulse/scenario";
import { getScenario, listScenarios, removeScenario, saveScenario } from "@/lib/pulse/scenarioStore";

function fresh(cityId: string, mode: ModeId): Scenario {
  const now = new Date().toISOString();
  return { id: newScenarioId(), cityId, name: "New line", mode, alignment: "elevated", stations: [], createdAt: now, updatedAt: now };
}

/** The line being built on the desk, its evaluation, and the saved library for this city. */
export function useLineScenario(model: CityModel, mode: ModeId, initial?: Scenario | null) {
  const cityId = model.city.id;
  const [line, setLine] = useState<Scenario | null>(initial ?? null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  const refresh = useCallback(() => setScenarios(listScenarios(cityId)), [cityId]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  // The mode picker applies to the line being built.
  useEffect(() => {
    setLine((l) => (l && l.mode !== mode ? { ...l, mode } : l));
  }, [mode]);

  const network = useMemo(() => (line && line.stations.length > 0 ? evaluateScenario(model, line) : null), [model, line]);

  const patch = useCallback((f: (l: Scenario) => Scenario) => {
    setLine((l) => (l ? { ...f(l), updatedAt: new Date().toISOString() } : l));
  }, []);

  const addStation = useCallback(
    (p: Point, name?: string) => {
      const { lat, lng } = model.grid.unproject(p);
      const station = { lat: Math.round(lat * 1e4) / 1e4, lng: Math.round(lng * 1e4) / 1e4, ...(name ? { name } : {}) };
      setLine((l) => {
        const base = l ?? fresh(cityId, mode);
        return { ...base, stations: [...base.stations, station], updatedAt: new Date().toISOString() };
      });
    },
    [model, cityId, mode]
  );

  const removeStation = useCallback((k: number) => patch((l) => ({ ...l, stations: l.stations.filter((_, i) => i !== k) })), [patch]);
  const moveStation = useCallback(
    (k: number, dir: -1 | 1) =>
      patch((l) => {
        const j = k + dir;
        if (j < 0 || j >= l.stations.length) return l;
        const s = l.stations.slice();
        [s[k], s[j]] = [s[j], s[k]];
        return { ...l, stations: s };
      }),
    [patch]
  );
  const setAlignment = useCallback((alignment: Alignment) => patch((l) => ({ ...l, alignment })), [patch]);
  const setCosts = useCallback((costs: CostTable) => patch((l) => ({ ...l, costs })), [patch]);
  const rename = useCallback((name: string) => patch((l) => ({ ...l, name })), [patch]);

  const save = useCallback(() => {
    if (!line) return;
    saveScenario(line);
    refresh();
  }, [line, refresh]);

  const open = useCallback((id: string): boolean => {
    const s = getScenario(id);
    if (!s) return false;
    setLine(s);
    return true;
  }, []);

  const remove = useCallback(
    (id: string) => {
      removeScenario(id);
      refresh();
    },
    [refresh]
  );

  const replace = useCallback((s: Scenario | null) => setLine(s), []);
  const clear = useCallback(() => setLine(null), []);

  return { line, network, scenarios, addStation, removeStation, moveStation, setAlignment, setCosts, rename, save, open, remove, replace, clear };
}

export type LineApi = ReturnType<typeof useLineScenario>;

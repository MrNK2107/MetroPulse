"use client";

import { useEffect, useId, useRef, useState } from "react";
import { getStateNames, resolvePlace } from "@/lib/twinApi";
import { useTwinStore } from "@/store/twinStore";
import type { Resolution } from "@/types/twin";

export function PlaceSearch() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState<Resolution | null>(null);
  const [states, setStates] = useState<Record<string, string>>({});
  const [failed, setFailed] = useState<string | null>(null);
  const selectPlace = useTwinStore((s) => s.selectPlace);
  const listId = useId();
  const skipNext = useRef(false);

  useEffect(() => {
    let live = true;
    getStateNames()
      .then((s) => live && setStates(s))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (skipNext.current) {
      skipNext.current = false;
      return;
    }
    const term = q.trim();
    if (!term) {
      setResult(null);
      setFailed(null);
      return;
    }
    let live = true;
    const t = setTimeout(() => {
      // M1 has district data only: a state or country match would be a card of No data.
      resolvePlace(term, { level: "district" })
        .then((r) => {
          if (!live) return;
          setResult(r);
          setFailed(null);
        })
        .catch((e) => {
          if (!live) return;
          setResult(null);
          setFailed(e instanceof Error ? e.message : "Search failed");
        });
    }, 250);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [q]);

  const pick = (id: string, name: string) => {
    void selectPlace(id);
    skipNext.current = name !== q;
    setQ(name);
    setResult(null);
  };

  return (
    <div className="w-80 max-w-[calc(100vw-2rem)] text-sm text-slate-100">
      <input
        type="search"
        role="searchbox"
        aria-label="Search for a district"
        aria-controls={listId}
        placeholder="Search a district"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            setResult(null);
          }
        }}
        className="w-full rounded-md border border-slate-600 bg-slate-900/95 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-400/40"
      />
      {failed && (
        <p role="status" className="mt-2 rounded-md bg-slate-900/95 px-3 py-2 text-sm text-red-300">
          {failed}
        </p>
      )}
      {result && (
        <div className="mt-2 overflow-hidden rounded-md border border-slate-700 bg-slate-900/95">
          {result.ambiguous && (
            <h2 className="px-3 pt-2 text-xs font-semibold uppercase tracking-wide text-amber-300">
              Which one?
            </h2>
          )}
          <ul id={listId} role="listbox" aria-label="Matching places">
            {result.matches.length === 0 && (
              <li className="px-3 py-2 text-slate-300">No matching place</li>
            )}
            {result.matches.map((m) => {
              const stateName = (m.stateCode && states[m.stateCode]) || m.stateCode || "";
              return (
                <li key={m.placeId} role="presentation">
                  <button
                    type="button"
                    role="option"
                    aria-selected={false}
                    onClick={() => pick(m.placeId, m.name)}
                    className="flex w-full items-baseline justify-between gap-3 px-3 py-2 text-left hover:bg-slate-800 focus:bg-slate-800 focus:outline-none"
                  >
                    <span>{m.name}</span>
                    <span className="text-xs text-slate-400">{stateName}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

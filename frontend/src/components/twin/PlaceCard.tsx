"use client";

import { useState } from "react";
import type { Observation, TrustLabel } from "@/types/twin";

const nf = new Intl.NumberFormat("en-IN");
const NOT_PUBLISHED = "Not published";

const CHIP: Record<TrustLabel, { label: string; cls: string }> = {
  fact: { label: "Fact", cls: "bg-emerald-900/70 text-emerald-200" },
  pattern: { label: "Pattern", cls: "bg-amber-900/70 text-amber-200" },
  projection: { label: "Projection", cls: "bg-sky-900/70 text-sky-200" },
};

function Row({ o }: { o: Observation }) {
  const [open, setOpen] = useState(false);
  const chip = o.trustLabel ? CHIP[o.trustLabel] : null;
  const rid = `receipt-${o.indicator}`;
  return (
    <li className="border-b border-slate-800 py-3">
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm text-slate-200">{o.name}</span>
        {chip && (
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${chip.cls}`}>{chip.label}</span>
        )}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        {o.value === null ? (
          <span className="text-sm text-slate-400">No data</span>
        ) : (
          <>
            <span className="text-lg font-semibold text-white">{nf.format(o.value)}</span>
            <span className="text-xs text-slate-400">{o.unit}</span>
          </>
        )}
        {o.period && <span className="ml-auto text-xs text-slate-400">{o.period}</span>}
      </div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={rid}
        onClick={() => setOpen((v) => !v)}
        className="mt-1 text-xs text-sky-300 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
      >
        {open ? "Hide source" : "Show source"}
      </button>
      {open && (
        <dl id={rid} className="mt-2 space-y-1 rounded bg-slate-900 p-2 text-xs text-slate-300">
          <div>
            <dt className="inline text-slate-400">Source: </dt>
            <dd className="inline">
              {o.receipt.url ? (
                <a
                  href={o.receipt.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sky-300 underline"
                >
                  {o.receipt.sourceName}
                </a>
              ) : (
                o.receipt.sourceName
              )}
            </dd>
          </div>
          <div>
            <dt className="inline text-slate-400">Dataset: </dt>
            <dd className="inline">{o.receipt.datasetVersion ?? NOT_PUBLISHED}</dd>
          </div>
          <div>
            <dt className="inline text-slate-400">Licence: </dt>
            <dd className="inline">{o.receipt.license ?? NOT_PUBLISHED}</dd>
          </div>
        </dl>
      )}
    </li>
  );
}

export function PlaceCard({
  name,
  stateName,
  observations,
}: {
  name: string;
  stateName: string | null;
  observations: Observation[];
}) {
  return (
    <div className="flex h-full flex-col text-slate-100">
      <header className="border-b border-slate-700 pb-3">
        <h2 className="text-xl font-semibold">{name}</h2>
        {stateName && <p className="text-sm text-slate-400">{stateName}</p>}
      </header>
      <ul className="flex-1 overflow-y-auto">
        {observations.map((o) => (
          <Row key={o.indicator} o={o} />
        ))}
      </ul>
      <footer className="pt-3 text-xs leading-relaxed text-slate-400">
        Census 2011 values for districts created after 2011 are apportioned by area. They&apos;re
        marked Pattern.
      </footer>
    </div>
  );
}

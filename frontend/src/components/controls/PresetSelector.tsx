"use client";

import { useState } from "react";
import { useSimulationStore } from "@/store/simulationStore";

interface Preset {
  name: string;
  city: string;
  description: string;
  prompt: string;
}

const PRESETS: Preset[] = [
  {
    name: "Tech Boom",
    city: "bengaluru",
    description: "Bengaluru IT/ITES growth with Digital India",
    prompt:
      "Bengaluru IT sector grows 30% with Digital India policy investment for 24 months",
  },
  {
    name: "Manufacturing Push",
    city: "chennai",
    description: "Chennai manufacturing expansion with Make in India",
    prompt:
      "Chennai manufacturing increases 25% with Make in India incentives for 24 months",
  },
  {
    name: "Real Estate Crisis",
    city: "mumbai",
    description: "Mumbai real estate decline with RERA compliance",
    prompt:
      "Mumbai real estate drops 20% while RERA compliance improves housing affordability for 12 months",
  },
  {
    name: "Infrastructure Focus",
    city: "delhi_ncr",
    description: "Delhi NCR transport investment with Smart City",
    prompt:
      "Delhi NCR transport logistics grows 15% with Smart City Mission infrastructure for 60 months",
  },
  {
    name: "Pharma SEZ",
    city: "hyderabad",
    description: "Hyderabad pharma SEZ expansion",
    prompt:
      "Hyderabad pharma manufacturing grows 20% with SEZ expansion and Make in India for 24 months",
  },
  {
    name: "Balanced Growth",
    city: "pune",
    description: "Pune multi-sector balanced development",
    prompt:
      "Pune all sectors grow 5% with AMRUT urban renewal for 24 months",
  },
];

export function PresetSelector() {
  const setScenarioText = useSimulationStore((s) => s.setScenarioText);
  const flyToCity = useSimulationStore((s) => s.flyToCity);
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="space-y-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between rounded-lg border border-dark-100/30 bg-dark-300/30 px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-500 transition-colors hover:border-blue-500/30 hover:text-blue-400"
      >
        <span>Quick Presets</span>
        <span className={`text-[10px] transition-transform ${isOpen ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>
      {isOpen && (
        <div className="grid grid-cols-2 gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => {
                setScenarioText(preset.prompt);
                flyToCity(preset.city);
                setIsOpen(false);
              }}
              className="rounded-xl border border-dark-100/40 bg-dark-300/35 p-3 text-left transition-all hover:border-blue-500/40 hover:bg-dark-200/50"
            >
              <p className="text-[11px] font-semibold text-white">{preset.name}</p>
              <p className="mt-0.5 text-[9px] text-gray-500">{preset.description}</p>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

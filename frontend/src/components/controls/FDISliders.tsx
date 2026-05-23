"use client";

import { useSimulationStore } from "@/store/simulationStore";

interface SliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  color: string;
}

function FDISlider({ label, value, onChange, color }: SliderProps) {
  const bgColor =
    value > 0 ? "bg-green-600" : value < 0 ? "bg-red-600" : "bg-gray-500";

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-300">{label}</span>
        <span className={`text-sm font-mono ${color}`}>
          {value > 0 ? "+" : ""}
          {value}%
        </span>
      </div>
      <input
        type="range"
        min={-100}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-dark-300 accent-current"
        style={{
          // @ts-ignore
          "--track-color": bgColor,
        }}
      />
      <div className="flex justify-between text-[10px] text-gray-500">
        <span>-100%</span>
        <span>0%</span>
        <span>+100%</span>
      </div>
    </div>
  );
}

export function FDISliders() {
  const fdi = useSimulationStore((s) => s.params.fdi);
  const setFDITech = useSimulationStore((s) => s.setFDITech);
  const setFDIManufacturing = useSimulationStore((s) => s.setFDIManufacturing);
  const setFDIRealEstate = useSimulationStore((s) => s.setFDIRealEstate);

  return (
    <div className="space-y-4">
      <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
        Foreign Direct Investment
      </h3>
      <FDISlider
        label="Technology"
        value={fdi.tech}
        onChange={setFDITech}
        color="text-blue-400"
      />
      <FDISlider
        label="Manufacturing"
        value={fdi.manufacturing}
        onChange={setFDIManufacturing}
        color="text-amber-400"
      />
      <FDISlider
        label="Real Estate"
        value={fdi.realEstate}
        onChange={setFDIRealEstate}
        color="text-purple-400"
      />
    </div>
  );
}

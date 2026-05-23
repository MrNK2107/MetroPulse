"use client";

import { create } from "zustand";
import type {
  SimulationParams,
  SimulationFrame,
  AggregateMetrics,
  SimulationStatus,
} from "@/types/simulation";

interface SimulationStore {
  params: SimulationParams;
  frames: SimulationFrame[];
  metrics: AggregateMetrics[];
  insight: string | null;
  status: SimulationStatus;
  error: string | null;
  simulationId: string | null;

  setParams: (params: Partial<SimulationParams>) => void;
  setFDITech: (value: number) => void;
  setFDIManufacturing: (value: number) => void;
  setFDIRealEstate: (value: number) => void;
  setPublicWorksZone: (zone: GeoJSON.GeoJSON | null) => void;
  setHorizonMonths: (months: 6 | 12 | 24 | 60) => void;
  addFrame: (frame: SimulationFrame) => void;
  setInsight: (markdown: string) => void;
  setStatus: (status: SimulationStatus) => void;
  setError: (error: string) => void;
  setSimulationId: (id: string) => void;
  reset: () => void;
}

const DEFAULT_PARAMS: SimulationParams = {
  fdi: { tech: 0, manufacturing: 0, realEstate: 0 },
  publicWorksZone: null,
  horizonMonths: 12,
};

export const useSimulationStore = create<SimulationStore>((set) => ({
  params: { ...DEFAULT_PARAMS },
  frames: [],
  metrics: [],
  insight: null,
  status: "idle",
  error: null,
  simulationId: null,

  setParams: (partial) =>
    set((state) => ({ params: { ...state.params, ...partial } })),

  setFDITech: (value) =>
    set((state) => ({
      params: { ...state.params, fdi: { ...state.params.fdi, tech: value } },
    })),

  setFDIManufacturing: (value) =>
    set((state) => ({
      params: {
        ...state.params,
        fdi: { ...state.params.fdi, manufacturing: value },
      },
    })),

  setFDIRealEstate: (value) =>
    set((state) => ({
      params: {
        ...state.params,
        fdi: { ...state.params.fdi, realEstate: value },
      },
    })),

  setPublicWorksZone: (zone) =>
    set((state) => ({ params: { ...state.params, publicWorksZone: zone } })),

  setHorizonMonths: (months) =>
    set((state) => ({ params: { ...state.params, horizonMonths: months } })),

  addFrame: (frame) =>
    set((state) => ({
      frames: [...state.frames, frame],
      metrics: [...state.metrics, frame.metrics],
    })),

  setInsight: (markdown) => set({ insight: markdown }),

  setStatus: (status) => set({ status }),

  setError: (error) => set({ error, status: "error" }),

  setSimulationId: (id) => set({ simulationId: id }),

  reset: () =>
    set({
      frames: [],
      metrics: [],
      insight: null,
      status: "idle",
      error: null,
      simulationId: null,
    }),
}));

import { create } from "zustand";
import { getObservations } from "@/lib/twinApi";
import type { Observation } from "@/types/twin";

interface TwinState {
  selectedPlaceId: string | null;
  observations: Observation[];
  loading: boolean;
  error: string | null;
  selectPlace: (id: string) => Promise<void>;
  clear: () => void;
}

export const useTwinStore = create<TwinState>((set, get) => ({
  selectedPlaceId: null,
  observations: [],
  loading: false,
  error: null,
  selectPlace: async (id) => {
    set({ selectedPlaceId: id, loading: true, error: null, observations: [] });
    try {
      const observations = await getObservations(id);
      if (get().selectedPlaceId !== id) return; // superseded
      set({ observations, loading: false });
    } catch (e) {
      if (get().selectedPlaceId !== id) return;
      set({
        observations: [],
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load place",
      });
    }
  },
  clear: () =>
    set({ selectedPlaceId: null, observations: [], loading: false, error: null }),
}));

"use client";

import { create } from "zustand";
import type {
  AggregateMetrics,
  CaseStudy,
  EvidenceReport,
  GroupImpact,
  ParsedScenario,
  PipelineStage,
  Prediction,
  SimulationFrame,
  WSGroupScoresMessage,
  WSNeedsInputMessage,
} from "@/types/simulation";
import type { MapMetricKey } from "@/lib/colorScale";

export type DrawMode = "none" | "point" | "polygon";

export interface ConversationMessage {
  role: "user" | "system";
  text: string;
  timestamp: number;
}

export interface StageEntry {
  stage: PipelineStage;
  message: string;
  status: "active" | "complete" | "error";
}

export const CITY_COORDS: Record<string, { center: [number, number]; zoom: number; name: string }> = {
  hyderabad: { center: [78.4867, 17.3850], zoom: 11, name: "Hyderabad" },
  bengaluru: { center: [77.5946, 12.9716], zoom: 11, name: "Bengaluru" },
  mumbai: { center: [72.8777, 19.0760], zoom: 11, name: "Mumbai" },
  delhi_ncr: { center: [77.2090, 28.6139], zoom: 10, name: "Delhi NCR" },
  chennai: { center: [80.2707, 13.0827], zoom: 11, name: "Chennai" },
  pune: { center: [73.8567, 18.5204], zoom: 11, name: "Pune" },
  kolkata: { center: [88.3639, 22.5726], zoom: 11, name: "Kolkata" },
  ahmedabad: { center: [72.5714, 23.0225], zoom: 11, name: "Ahmedabad" },
  jaipur: { center: [75.7873, 26.9124], zoom: 11, name: "Jaipur" },
  lucknow: { center: [80.9462, 26.8467], zoom: 11, name: "Lucknow" },
  chandigarh: { center: [76.7794, 30.7333], zoom: 12, name: "Chandigarh" },
  bhubaneswar: { center: [85.8245, 20.2961], zoom: 12, name: "Bhubaneswar" },
};

interface SimulationStore {
  scenarioText: string;
  parsedScenario: ParsedScenario | null;
  prediction: Prediction | null;
  frames: SimulationFrame[];
  metrics: AggregateMetrics[];
  caseStudies: CaseStudy[];
  evidence: EvidenceReport | null;
  pipelineStage: PipelineStage;
  stageHistory: StageEntry[];
  error: string | null;
  errorStage: PipelineStage | null;
  simulationId: string | null;

  // Conversation state
  conversationMessages: ConversationMessage[];
  conversationMode: "quick" | "deep";
  pendingQuestion: WSNeedsInputMessage | null;
  groupScores: GroupImpact[];
  citizenSatisfaction: number | null;

  drawMode: DrawMode;
  pendingVertices: [number, number][];
  publicWorksZone: GeoJSON.GeoJSON | null;
  activeFrameIndex: number;
  regionBoundary: GeoJSON.GeoJSON | null;

  // Visual Overlay & Layout HUD States
  activeVisualizationMode: "heatmap" | "flat" | "3d";
  activeMetric: MapMetricKey;
  isLeftSidebarOpen: boolean;
  isRightSidebarOpen: boolean;
  isBottomDrawerOpen: boolean;
  mapViewState: {
    longitude: number;
    latitude: number;
    zoom: number;
    pitch: number;
    bearing: number;
  };

  setScenarioText: (value: string) => void;
  setStage: (stage: PipelineStage, message: string) => void;
  setParsedScenario: (params: ParsedScenario) => void;
  setPrediction: (prediction: Prediction) => void;
  addFrame: (frame: SimulationFrame) => void;
  setCaseStudies: (studies: CaseStudy[]) => void;
  setEvidence: (report: EvidenceReport) => void;
  setError: (error: string, stage?: PipelineStage) => void;
  setSimulationId: (id: string) => void;
  setDrawMode: (mode: DrawMode) => void;
  addZoneVertex: (coord: [number, number]) => void;
  removeLastVertex: () => void;
  finishPolygon: () => void;
  setPublicWorksZone: (zone: GeoJSON.GeoJSON | null) => void;
  setRegionBoundary: (boundary: GeoJSON.GeoJSON | null) => void;
  setActiveFrameIndex: (index: number) => void;
  setHorizonMonths: (months: 6 | 12 | 24 | 60) => void;
  adjustSectorDelta: (sector: string, value: number) => void;

  setActiveVisualizationMode: (mode: "heatmap" | "flat" | "3d") => void;
  setActiveMetric: (metric: MapMetricKey) => void;
  setLeftSidebarOpen: (open: boolean) => void;
  setRightSidebarOpen: (open: boolean) => void;
  setBottomDrawerOpen: (open: boolean) => void;
  setMapViewState: (viewState: any) => void;
  flyToCity: (cityId: string) => void;

  addConversationMessage: (role: "user" | "system", text: string) => void;
  setPendingQuestion: (question: WSNeedsInputMessage | null) => void;
  setConversationMode: (mode: "quick" | "deep") => void;
  setGroupScores: (msg: WSGroupScoresMessage) => void;

  resetRun: () => void;
  resetAll: () => void;
}

const EXAMPLE =
  "What happens to Hyderabad if pharma FDI drops 40% but Smart City Mission continues for 24 months?";

const DEFAULT_MAP_VIEW_STATE = {
  longitude: 78.4867,
  latitude: 17.385,
  zoom: 11,
  pitch: 30, // Default to a shallower pitch for flatter Heatmap/Flat tracing views
  bearing: 0,
};

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  scenarioText: EXAMPLE,
  parsedScenario: null,
  prediction: null,
  frames: [],
  metrics: [],
  caseStudies: [],
  evidence: null,
  pipelineStage: "idle",
  stageHistory: [],
  error: null,
  errorStage: null,
  simulationId: null,

  conversationMessages: [],
  conversationMode: "quick",
  pendingQuestion: null,
  groupScores: [],
  citizenSatisfaction: null,

  drawMode: "none",
  pendingVertices: [],
  publicWorksZone: null,
  activeFrameIndex: -1,
  regionBoundary: null,

  // HUD Defaults: Trace Heatmap as requested, collapsible sidebars open initially
  activeVisualizationMode: "flat",
  activeMetric: "delta",
  isLeftSidebarOpen: true,
  isRightSidebarOpen: true,
  isBottomDrawerOpen: false,
  mapViewState: DEFAULT_MAP_VIEW_STATE,

  setScenarioText: (value) => set({ scenarioText: value }),

  setStage: (stage, message) =>
    set((state) => {
      const completed = state.stageHistory.map((entry) =>
        entry.status === "active" ? { ...entry, status: "complete" as const } : entry
      );
      return {
        pipelineStage: stage,
        stageHistory: [...completed, { stage, message, status: "active" }],
      };
    }),

  setParsedScenario: (params) => {
    set({ parsedScenario: params, publicWorksZone: params.public_works_zone });
    // Automatically center map viewport on resolved city
    const resolvedCity = params.city.toLowerCase().replace(" ", "_");
    const cityConfig = CITY_COORDS[resolvedCity];
    if (cityConfig) {
      set({
        mapViewState: {
          longitude: cityConfig.center[0],
          latitude: cityConfig.center[1],
          zoom: cityConfig.zoom,
          pitch: get().activeVisualizationMode === "3d" ? 45 : 0, // Flatten map if Heatmap/Flat mode
          bearing: 0,
        },
      });
    }
  },

  setPrediction: (prediction) => set({ prediction }),

  addFrame: (frame) =>
    set((state) => {
      const frames = [...state.frames, frame];
      return {
        frames,
        metrics: [...state.metrics, frame.metrics],
        activeFrameIndex: frames.length - 1,
      };
    }),

  setCaseStudies: (studies) => set({ caseStudies: studies }),

  setEvidence: (report) => set({ evidence: report }),

  setError: (error, stage) =>
    set((state) => ({
      error,
      errorStage: stage ?? state.pipelineStage,
      pipelineStage: "error",
      stageHistory: [
        ...state.stageHistory.map((entry) =>
          entry.status === "active" ? { ...entry, status: "error" as const } : entry
        ),
      ],
    })),

  setSimulationId: (id) =>
    set((state) => ({
      simulationId: id,
      pipelineStage: "done",
      stageHistory: state.stageHistory.map((entry) =>
        entry.status === "active" ? { ...entry, status: "complete" as const } : entry
      ),
    })),

  setDrawMode: (mode) => set({ drawMode: mode, pendingVertices: [] }),

  addZoneVertex: (coord) =>
    set((state) => ({ pendingVertices: [...state.pendingVertices, coord] })),

  removeLastVertex: () =>
    set((state) => ({ pendingVertices: state.pendingVertices.slice(0, -1) })),

  finishPolygon: () => {
    const { pendingVertices } = get();
    if (pendingVertices.length < 3) return;
    const coords = [
      ...pendingVertices.map(([lng, lat]) => [lng, lat]),
      [pendingVertices[0][0], pendingVertices[0][1]],
    ];
    const polygon: GeoJSON.Polygon = { type: "Polygon", coordinates: [coords] };
    set({ publicWorksZone: polygon, drawMode: "none", pendingVertices: [] });
  },

  setPublicWorksZone: (zone) => set({ publicWorksZone: zone }),
  setRegionBoundary: (boundary) => set({ regionBoundary: boundary }),

  setActiveFrameIndex: (index) => set({ activeFrameIndex: index }),

  setHorizonMonths: (months) =>
    set((state) => ({
      parsedScenario: state.parsedScenario
        ? { ...state.parsedScenario, horizon_months: months }
        : null,
    })),

  adjustSectorDelta: (sector, value) =>
    set((state) => ({
      parsedScenario: state.parsedScenario
        ? {
            ...state.parsedScenario,
            sector_deltas: { ...state.parsedScenario.sector_deltas, [sector]: value },
          }
        : null,
    })),

  setActiveVisualizationMode: (mode) => {
    set((state) => ({
      activeVisualizationMode: mode,
      mapViewState: {
        ...state.mapViewState,
        pitch: mode === "3d" ? 45 : 0,
      },
    }));
  },

  setActiveMetric: (metric) => set({ activeMetric: metric }),
  setLeftSidebarOpen: (open) => set({ isLeftSidebarOpen: open }),
  setRightSidebarOpen: (open) => set({ isRightSidebarOpen: open }),
  setBottomDrawerOpen: (open) => set({ isBottomDrawerOpen: open }),
  setMapViewState: (viewState) => set({ mapViewState: viewState }),
  flyToCity: (cityId) => {
    const cityConfig = CITY_COORDS[cityId];
    if (cityConfig) {
      set((state) => ({
        mapViewState: {
          longitude: cityConfig.center[0],
          latitude: cityConfig.center[1],
          zoom: cityConfig.zoom,
          pitch: state.activeVisualizationMode === "3d" ? 45 : 0,
          bearing: 0,
        },
      }));
    }
  },

  addConversationMessage: (role, text) =>
    set((state) => ({
      conversationMessages: [
        ...state.conversationMessages,
        { role, text, timestamp: Date.now() },
      ],
    })),

  setPendingQuestion: (question) => set({ pendingQuestion: question }),

  setConversationMode: (mode) => set({ conversationMode: mode }),

  setGroupScores: (msg) =>
    set({
      groupScores: msg.groups,
      citizenSatisfaction: msg.citizen_satisfaction,
    }),

  resetRun: () =>
    set({
      parsedScenario: null,
      prediction: null,
      frames: [],
      metrics: [],
      caseStudies: [],
      evidence: null,
      pipelineStage: "idle",
      stageHistory: [],
      error: null,
      errorStage: null,
      simulationId: null,
      activeFrameIndex: -1,
      conversationMessages: [],
      pendingQuestion: null,
      groupScores: [],
      citizenSatisfaction: null,
    }),

  resetAll: () =>
    set({
      scenarioText: EXAMPLE,
      parsedScenario: null,
      prediction: null,
      frames: [],
      metrics: [],
      caseStudies: [],
      evidence: null,
      pipelineStage: "idle",
      stageHistory: [],
      error: null,
      errorStage: null,
      simulationId: null,
      drawMode: "none",
      pendingVertices: [],
      publicWorksZone: null,
      activeFrameIndex: -1,
      // Maintain UI choices (active visualization / metric)
      mapViewState: DEFAULT_MAP_VIEW_STATE,
    }),
}));



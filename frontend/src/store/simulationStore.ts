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
  SnapshotSummary,
  WSGroupScoresMessage,
  WSNeedsInputMessage,
} from "@/types/simulation";
import type { MapMetricKey } from "@/lib/colorScale";

export type DrawMode = "none" | "point" | "polygon";

export interface SimulationHistoryEntry {
  id: string;
  city: string;
  scenario: string;
  timestamp: number;
  verdict: string;
}

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
  indore: { center: [75.8577, 22.7196], zoom: 11, name: "Indore" },
  surat: { center: [72.8311, 21.1702], zoom: 11, name: "Surat" },
  nagpur: { center: [79.0882, 21.1458], zoom: 11, name: "Nagpur" },
  visakhapatnam: { center: [83.3013, 17.6868], zoom: 11, name: "Visakhapatnam" },
  kochi: { center: [76.2674, 9.9312], zoom: 11, name: "Kochi" },
  coimbatore: { center: [76.9558, 11.0168], zoom: 11, name: "Coimbatore" },
  patna: { center: [85.1376, 25.6093], zoom: 11, name: "Patna" },
  bhopal: { center: [77.4126, 23.2599], zoom: 11, name: "Bhopal" },
  vadodara: { center: [73.1812, 22.3072], zoom: 11, name: "Vadodara" },
  ludhiana: { center: [75.8573, 30.9010], zoom: 11, name: "Ludhiana" },
  agra: { center: [78.0081, 27.1767], zoom: 11, name: "Agra" },
  varanasi: { center: [82.9739, 25.3176], zoom: 11, name: "Varanasi" },
  rajkot: { center: [70.8022, 22.3039], zoom: 11, name: "Rajkot" },
  amritsar: { center: [74.8723, 31.6340], zoom: 11, name: "Amritsar" },
  ranchi: { center: [85.3096, 23.3441], zoom: 11, name: "Ranchi" },
  guwahati: { center: [91.7362, 26.1445], zoom: 11, name: "Guwahati" },
  mysuru: { center: [76.6394, 12.2958], zoom: 11, name: "Mysuru" },
  dehradun: { center: [78.0322, 30.3165], zoom: 11, name: "Dehradun" },
};

/** Shared selector: derives the currently-active simulation frame. */
export const selectCurrentFrame = (state: SimulationStore) =>
  state.frames.length > 0 && state.activeFrameIndex >= 0
    ? state.frames[Math.min(state.activeFrameIndex, state.frames.length - 1)]
    : null;

interface SimulationStore {
  scenarioText: string;
  parsedScenario: ParsedScenario | null;
  prediction: Prediction | null;
  frames: SimulationFrame[];
  metrics: AggregateMetrics[];
  getMetrics: () => AggregateMetrics[];
  caseStudies: CaseStudy[];
  evidence: EvidenceReport | null;
  pipelineStage: PipelineStage;
  stageHistory: StageEntry[];
  error: string | null;
  errorStage: PipelineStage | null;
  simulationId: string | null;
  snapshot: SnapshotSummary | null;

  // Simulation history
  simulationHistory: SimulationHistoryEntry[];

  // Duration tracking
  simulationStartTime: number | null;
  simulationDuration: number | null;

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
  comparisonMode: boolean;
  comparisonSimulation: SimulationHistoryEntry | null;
  loadingCities: boolean;

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
  cityCoords: Record<string, { center: [number, number]; zoom: number; name: string }>;

  setScenarioText: (value: string) => void;
  setStage: (stage: PipelineStage, message: string) => void;
  setParsedScenario: (params: ParsedScenario, snapshot?: SnapshotSummary) => void;
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
  setHorizonMonths: (months: number) => void;
  adjustSectorDelta: (sector: string, value: number) => void;

  setActiveVisualizationMode: (mode: "heatmap" | "flat" | "3d") => void;
  setActiveMetric: (metric: MapMetricKey) => void;
  setLeftSidebarOpen: (open: boolean) => void;
  setRightSidebarOpen: (open: boolean) => void;
  setBottomDrawerOpen: (open: boolean) => void;
  setMapViewState: (viewState: SimulationStore["mapViewState"]) => void;
  flyToCity: (cityId: string) => void;
  loadCityCoords: () => Promise<void>;

  addConversationMessage: (role: "user" | "system", text: string) => void;
  setPendingQuestion: (question: WSNeedsInputMessage | null) => void;
  setConversationMode: (mode: "quick" | "deep") => void;
  setGroupScores: (msg: WSGroupScoresMessage) => void;

  resetRun: () => void;
  resetAll: () => void;
}

const EXAMPLE_SCENARIOS = [
  "What happens to Hyderabad if pharma FDI drops 40% but Smart City Mission continues for 24 months?",
  "Bengaluru tech sector grows 25% with Digital India expansion over 2 years",
  "Mumbai port trade declines 15% due to global shipping disruptions for 12 months",
  "Chennai manufacturing gets a 30% Make in India boost alongside AMRUT upgrades",
  "Pune auto industry faces 20% decline while RERA compliance continues for 24 months",
  "Ahmedabad textile exports surge 35% with new SEZ notification for 60 months",
];

const EXAMPLE = EXAMPLE_SCENARIOS[Math.floor(Math.random() * EXAMPLE_SCENARIOS.length)];

const HISTORY_KEY = "metropulse-simulation-history";

function loadHistory(): SimulationHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(history: SimulationHistoryEntry[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 10)));
  } catch { /* storage full */ }
}

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
  snapshot: null,
  simulationHistory: loadHistory(),

  // Duration tracking
  simulationStartTime: null,
  simulationDuration: null,

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
  comparisonMode: false,
  comparisonSimulation: null,
  loadingCities: false,

  // HUD Defaults: Trace Heatmap as requested, collapsible sidebars open initially
  activeVisualizationMode: "flat",
  activeMetric: "delta",
  isLeftSidebarOpen: true,
  isRightSidebarOpen: true,
  isBottomDrawerOpen: false,
  mapViewState: DEFAULT_MAP_VIEW_STATE,

  // Dynamic city coordinates — starts with static fallback, updated from API
  cityCoords: { ...CITY_COORDS },

  setScenarioText: (value) => set({ scenarioText: value }),

  setStage: (stage, message) =>
    set((state) => {
      const completed = state.stageHistory.map((entry) =>
        entry.status === "active" ? { ...entry, status: "complete" as const } : entry
      );
      // Capture start time on first stage transition (when idle)
      const startTime = state.pipelineStage === "idle" ? Date.now() : state.simulationStartTime;
      return {
        pipelineStage: stage,
        stageHistory: [...completed, { stage, message, status: "active" }],
        simulationStartTime: startTime,
      };
    }),

  setParsedScenario: (params, snapshot) => {
    set({ parsedScenario: params, publicWorksZone: params.public_works_zone, snapshot: snapshot ?? null });
    // Automatically center map viewport on resolved city
    const resolvedCity = params.city.toLowerCase().replaceAll(" ", "_");
    const cityConfig = get().cityCoords[resolvedCity];
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

  getMetrics: () => get().frames.map((f) => f.metrics),

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
    set((state) => {
      const newEntry: SimulationHistoryEntry = {
        id,
        city: state.parsedScenario?.city ?? "unknown",
        scenario: state.scenarioText,
        timestamp: Date.now(),
        verdict: state.evidence?.translation?.overall_verdict ?? "",
      };
      const updatedHistory = [newEntry, ...state.simulationHistory].slice(0, 10);
      saveHistory(updatedHistory);
      // Compute duration from start time
      const duration = state.simulationStartTime
        ? (Date.now() - state.simulationStartTime) / 1000
        : null;
      return {
        simulationId: id,
        pipelineStage: "done",
        simulationHistory: updatedHistory,
        simulationDuration: duration,
        stageHistory: state.stageHistory.map((entry) =>
          entry.status === "active" ? { ...entry, status: "complete" as const } : entry
        ),
      };
    }),

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
            sector_deltas: {
              ...state.parsedScenario.sector_deltas,
              [sector]: Math.max(-100, Math.min(100, value)),
            },
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
    const cityConfig = get().cityCoords[cityId];
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

  setConversationMode: (mode) =>
    set((state) => {
      const nextState: Partial<SimulationStore> = { conversationMode: mode };
      if (mode === "deep" && !state.parsedScenario) {
        nextState.parsedScenario = {
          city: "mumbai",
          sector_deltas: {
            it_ites: 0,
            manufacturing: 0,
            real_estate: 0,
            trade_hospitality: 0,
            transport_logistics: 0,
            informal: 0,
            public_admin: 0,
          },
          policies_active: [],
          public_works_zone: null,
          horizon_months: 24,
          causal_chain: "Direct parameter specification",
          keywords: ["mumbai"],
          confidence: "high",
          assumptions: ["Direct numeric specification by user."],
        };
      }
      return nextState;
    }),

  setGroupScores: (msg) =>
    set({
      groupScores: msg.groups,
      citizenSatisfaction: msg.citizen_satisfaction,
    }),

  loadCityCoords: async () => {
    set({ loadingCities: true });
    try {
      const res = await fetch("/api/regions");
      if (!res.ok) return;
      const json = await res.json();
      const regions = json.data as Array<{ id: string; center: [number, number]; zoom: number; name: string }>;
      if (!Array.isArray(regions)) return;
      const dynamic: Record<string, { center: [number, number]; zoom: number; name: string }> = {};
      for (const r of regions) {
        if (r.id && r.center && r.zoom) {
          dynamic[r.id] = { center: r.center, zoom: r.zoom, name: r.name };
        }
      }
      set({ cityCoords: { ...CITY_COORDS, ...dynamic }, loadingCities: false });
    } catch {
      // API unavailable — keep static fallback
      set({ loadingCities: false });
    }
  },

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
      snapshot: null,
      activeFrameIndex: -1,
      conversationMessages: [],
      pendingQuestion: null,
      groupScores: [],
      citizenSatisfaction: null,
      comparisonMode: false,
      comparisonSimulation: null,
      simulationStartTime: null,
      simulationDuration: null,
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
      snapshot: null,
      conversationMessages: [],
      pendingQuestion: null,
      groupScores: [],
      citizenSatisfaction: null,
      drawMode: "none",
      pendingVertices: [],
      publicWorksZone: null,
      activeFrameIndex: -1,
      // Maintain UI choices (active visualization / metric)
      mapViewState: DEFAULT_MAP_VIEW_STATE,
      simulationStartTime: null,
      simulationDuration: null,
    }),
}));



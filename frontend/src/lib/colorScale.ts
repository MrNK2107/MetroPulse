export type RGBA = [number, number, number, number];

export type MapMetricKey = "delta" | "jobDensity" | "congestion" | "realEstateIndex" | "floodRisk";

export interface ColorStop {
  value: number;
  color: [number, number, number];
}

// Color stops for each metric to create vibrant, meaningful visual gradients
export const METRIC_SCALES: Record<MapMetricKey, { stops: ColorStop[]; clamp: [number, number]; label: string }> = {
  delta: {
    label: "Economic Impact (Δ GDP)",
    clamp: [-0.15, 0.15],
    stops: [
      { value: -0.15, color: [239, 68, 68] },  // Red-500 (Stress)
      { value: -0.05, color: [249, 115, 22] }, // Orange-500 (Muted Stress)
      { value: 0.0, color: [71, 85, 105] },    // Slate-600 (Stable Neutral)
      { value: 0.05, color: [56, 189, 248] },  // Sky-400 (Muted Growth)
      { value: 0.15, color: [59, 130, 246] },  // Blue-500 (Growth)
    ],
  },
  jobDensity: {
    label: "Total Job Density (Viridis)",
    clamp: [0, 8000],
    stops: [
      { value: 0, color: [68, 1, 84] },        // Purple (Viridis)
      { value: 2000, color: [59, 82, 139] },    // Blue (Viridis)
      { value: 4000, color: [33, 145, 140] },   // Teal (Viridis)
      { value: 8000, color: [94, 201, 98] },    // Green (Viridis)
    ],
  },
  congestion: {
    label: "Transit Congestion (Magma)",
    clamp: [0.0, 1.0],
    stops: [
      { value: 0.0, color: [71, 85, 105] },    // Slate neutral
      { value: 0.3, color: [182, 54, 121] },   // Purple/Pink (Magma)
      { value: 0.7, color: [251, 136, 97] },   // Orange (Magma)
      { value: 1.0, color: [252, 253, 191] },  // Yellow/White (Magma)
    ],
  },
  realEstateIndex: {
    label: "Real Estate Index",
    clamp: [0.3, 2.2],
    stops: [
      { value: 0.3, color: [68, 1, 84] },       // Purple (Viridis/Magma)
      { value: 1.0, color: [139, 92, 246] },   // Violet-500
      { value: 1.6, color: [192, 132, 252] },  // Purple-400
      { value: 2.2, color: [253, 231, 37] },   // Yellow (Viridis)
    ],
  },
  floodRisk: {
    label: "Flood Risk Index",
    clamp: [0.0, 1.0],
    stops: [
      { value: 0.0, color: [71, 85, 105] },    // Slate-600
      { value: 0.4, color: [56, 189, 248] },   // Sky-400
      { value: 1.0, color: [29, 78, 216] },    // Blue-700
    ],
  },
};

function lerpColor(t: number, a: [number, number, number], b: [number, number, number]): [number, number, number] {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

export function metricToRGBA(value: number, metric: MapMetricKey = "delta"): RGBA {
  const { stops, clamp } = METRIC_SCALES[metric];
  const clamped = Math.max(clamp[0], Math.min(clamp[1], value));

  let lower = stops[0];
  let upper = stops[stops.length - 1];

  for (let i = 0; i < stops.length - 1; i++) {
    if (clamped >= stops[i].value && clamped <= stops[i + 1].value) {
      lower = stops[i];
      upper = stops[i + 1];
      break;
    }
  }

  const range = upper.value - lower.value;
  const t = range === 0 ? 0 : (clamped - lower.value) / range;
  const [r, g, b] = lerpColor(t, lower.color, upper.color);

  // Set transparency based on the metric intensity, ensuring base layers remain clear
  let alpha = 160;
  if (metric === "delta") {
    // Stable slate is more transparent, while growth and stress glow brighter
    const dev = Math.abs(clamped);
    alpha = Math.round(110 + (dev / 0.15) * 145);
  } else {
    // Normal normalized index opacity
    const rangeSpan = clamp[1] - clamp[0];
    const pct = rangeSpan === 0 ? 0 : (clamped - clamp[0]) / rangeSpan;
    alpha = Math.round(120 + pct * 135);
  }

  return [r, g, b, Math.min(255, Math.max(0, alpha))];
}

// Legacy compatibility wrapper
export function deltaToRGBA(delta: number, _height: number): RGBA {
  return metricToRGBA(delta, "delta");
}

export function getLegendStops(metric: MapMetricKey = "delta"): { value: number; color: string }[] {
  return METRIC_SCALES[metric].stops.map((stop) => ({
    value: stop.value,
    color: `rgb(${stop.color[0]}, ${stop.color[1]}, ${stop.color[2]})`,
  }));
}

export function formatDelta(delta: number): string {
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${(delta * 100).toFixed(1)}%`;
}

/**
 * Normalize a metric value to [0, 100] for HeatmapLayer (requires non-negative weights).
 * For delta, we want absolute deviation from 0.0 to glow (0% change = 0 weight, 15%+ change = 100 weight)
 * raised to a power to suppress small fluctuations.
 * For sequential metrics, we suppress low background values using a power of 2.
 */
export function heatmapWeight(value: number, metric: MapMetricKey): number {
  if (Number.isNaN(value) || value === undefined) return 0;
  const { clamp } = METRIC_SCALES[metric];

  if (metric === "delta") {
    // For delta, absolute deviation from 0.0 (maximum expected is 0.15)
    const absVal = Math.abs(value);
    const normalized = absVal / 0.15;
    return Math.max(0, Math.min(100, Math.pow(normalized, 1.8) * 100));
  }

  const normalized = (value - clamp[0]) / (clamp[1] - clamp[0]);
  const clamped = Math.max(0, Math.min(1.0, normalized));
  return Math.max(0, Math.min(100, Math.pow(clamped, 2.0) * 100));
}

/**
 * Returns a 6-color RGB array for HeatmapLayer, appropriate for the given metric.
 * Delta uses diverging (stress=warm, growth=cool). Others use sequential palettes.
 */
export function heatmapColorRange(metric: MapMetricKey): [number, number, number][] {
  if (metric === "delta") {
    return [
      [239, 68, 68],    // Red-500 (strong negative / stress)
      [249, 115, 22],   // Orange-500 (mild negative)
      [148, 163, 184],  // Slate-400 (neutral)
      [148, 163, 184],  // Slate-400 (neutral)
      [56, 189, 248],   // Sky-400 (mild positive)
      [59, 130, 246],   // Blue-500 (strong positive / growth)
    ];
  }
  if (metric === "jobDensity") {
    return [
      [30, 41, 59],     // Dark Slate
      [68, 1, 84],      // Viridis Purple
      [59, 82, 139],    // Viridis Blue
      [33, 145, 140],   // Viridis Teal
      [94, 201, 98],    // Viridis Green
      [253, 231, 37],   // Viridis Yellow
    ];
  }
  if (metric === "congestion") {
    return [
      [30, 41, 59],
      [71, 85, 105],
      [182, 54, 121],   // Purple/Pink
      [251, 136, 97],   // Orange
      [252, 200, 120],  // Light Orange
      [252, 253, 191],  // Yellow/White
    ];
  }
  if (metric === "realEstateIndex") {
    return [
      [30, 41, 59],
      [68, 1, 84],
      [139, 92, 246],   // Violet-500
      [192, 132, 252],  // Purple-400
      [236, 72, 153],   // Pink-500
      [253, 231, 37],   // Yellow
    ];
  }
  // floodRisk
  return [
    [30, 41, 59],
    [71, 85, 105],
    [56, 189, 248],     // Sky-400
    [14, 165, 233],     // Sky-500
    [29, 78, 216],      // Blue-700
    [30, 58, 138],      // Blue-900
  ];
}


export type RGBA = [number, number, number, number];

export function deltaToRGBA(delta: number, _height: number): RGBA {
  if (delta > 0.1) return [34, 197, 94, 200];
  if (delta < -0.1) return [239, 68, 68, 200];
  return [251, 191, 36, 200];
}

export function formatDelta(delta: number): string {
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${(delta * 100).toFixed(1)}%`;
}

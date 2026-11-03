/** Hour-of-week helpers shared by the model, the detector and siting. */
export const HOURS_PER_WEEK = 168;
export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

export function dayHourLabel(h: number): string {
  const d = Math.floor(h / 24) % 7;
  return `${DAYS[d]} ${String(h % 24).padStart(2, "0")}:00`;
}

export function hourLabel(h: number): string {
  return `${String(h % 24).padStart(2, "0")}:00`;
}

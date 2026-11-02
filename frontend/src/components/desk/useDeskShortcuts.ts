"use client";

import { useEffect, useRef } from "react";

export interface DeskShortcutActions {
  togglePlay: () => void;
  /** Move the timeline by `delta` hours (wraps around the week). */
  step: (delta: number) => void;
  tab: (index: 0 | 1 | 2) => void;
  /** Next (+1) or previous (-1) incident; opens Alerts. */
  incident: (dir: 1 | -1) => void;
  copyLink: () => void;
  exportCsv: () => void;
  openBriefing: () => void;
  escape: () => void;
  toggleHelp: () => void;
}

export const DESK_SHORTCUTS: { keys: string[]; does: string }[] = [
  { keys: ["Space"], does: "Play or pause the week" },
  { keys: ["←", "→"], does: "Step one hour" },
  { keys: ["Shift", "← / →"], does: "Step one day" },
  { keys: ["1", "2", "3"], does: "Pulse, Alerts, Siting" },
  { keys: ["J", "K"], does: "Next or previous incident" },
  { keys: ["L"], does: "Copy a link to this view" },
  { keys: ["E"], does: "Download this week's incidents as CSV" },
  { keys: ["B"], does: "Open the printable briefing" },
  { keys: ["Esc"], does: "Close, deselect or clear the pin" },
  { keys: ["?"], does: "Show or hide this list" },
];

/** Typing in a field, or a key the focused control already handles, is not a shortcut. */
function ignore(e: KeyboardEvent): boolean {
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return true;
  const t = e.target as HTMLElement | null;
  if (!t || typeof t.closest !== "function") return false;
  if (t.isContentEditable || t.closest("input, textarea, select, [contenteditable='true']")) return true;
  // Space and Enter already activate a focused button or link.
  if ((e.key === " " || e.key === "Enter") && t.closest("button, a, summary")) return true;
  return false;
}

export function useDeskShortcuts(actions: DeskShortcutActions, enabled = true): void {
  const ref = useRef(actions);
  ref.current = actions;

  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (ignore(e)) return;
      const a = ref.current;
      let handled = true;
      switch (e.key) {
        case " ":
          a.togglePlay();
          break;
        case "ArrowRight":
          a.step(e.shiftKey ? 24 : 1);
          break;
        case "ArrowLeft":
          a.step(e.shiftKey ? -24 : -1);
          break;
        case "1":
        case "2":
        case "3":
          a.tab((Number(e.key) - 1) as 0 | 1 | 2);
          break;
        case "j":
        case "J":
          a.incident(1);
          break;
        case "k":
        case "K":
          a.incident(-1);
          break;
        case "l":
        case "L":
          a.copyLink();
          break;
        case "e":
        case "E":
          a.exportCsv();
          break;
        case "b":
        case "B":
          a.openBriefing();
          break;
        case "Escape":
          a.escape();
          break;
        case "?":
          a.toggleHelp();
          break;
        default:
          handled = false;
      }
      if (handled) e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}

"use client";

import { useEffect, useRef } from "react";
import { DESK_SHORTCUTS } from "./useDeskShortcuts";

interface Props {
  open: boolean;
  onClose: () => void;
}

/** Keyboard shortcuts as a modal dialog: focus moves in, Tab is trapped, Esc closes and focus goes back. */
export function ShortcutsHelp({ open, onClose }: Props) {
  const dialog = useRef<HTMLDivElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    closeBtn.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "?") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !dialog.current) return;
      const items = dialog.current.querySelectorAll<HTMLElement>("button, [href], [tabindex]:not([tabindex='-1'])");
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    // Capture phase, so the desk's own shortcuts never see keys meant for the dialog.
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      previous?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="no-print fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" onClick={onClose}>
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md border-2 border-ink bg-paper p-5 shadow-[6px_6px_0_0_#16130F]"
      >
        <div className="flex items-baseline justify-between">
          <h2 id="shortcuts-title" className="font-display text-xl font-semibold">
            Keyboard shortcuts
          </h2>
          <button
            ref={closeBtn}
            type="button"
            onClick={onClose}
            className="border border-ink px-2 py-0.5 font-mono text-[11px] uppercase tracking-widest hover:bg-paper-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            Close
          </button>
        </div>
        <dl className="mt-3 divide-y divide-ink/15">
          {DESK_SHORTCUTS.map((s) => (
            <div key={s.does} className="flex items-center justify-between gap-4 py-1.5 text-sm">
              <dt className="flex shrink-0 gap-1">
                {s.keys.map((k) => (
                  <kbd key={k} className="border border-ink/60 bg-paper-deep px-1.5 py-0.5 font-mono text-[11px]">
                    {k}
                  </kbd>
                ))}
              </dt>
              <dd className="text-right text-ink-soft">{s.does}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          Shortcuts pause while you type in a field.
        </p>
      </div>
    </div>
  );
}

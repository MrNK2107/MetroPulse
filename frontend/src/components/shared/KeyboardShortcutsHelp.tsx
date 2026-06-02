"use client";

import React, { useEffect } from "react";

interface ShortcutGroup {
  title: string;
  shortcuts: { keys: string; description: string }[];
}

const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    title: "Simulation",
    shortcuts: [
      { keys: "Ctrl + Enter", description: "Run simulation" },
    ],
  },
  {
    title: "Timeline Navigation",
    shortcuts: [
      { keys: "←", description: "Previous frame" },
      { keys: "→", description: "Next frame" },
    ],
  },
  {
    title: "Drawing Tools",
    shortcuts: [
      { keys: "Esc", description: "Exit drawing mode" },
    ],
  },
  {
    title: "General",
    shortcuts: [
      { keys: "?", description: "Toggle keyboard shortcuts help" },
    ],
  },
];

interface KeyboardShortcutsHelpProps {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard Shortcuts"
    >
      <div
        className="bg-dark-200/98 border border-dark-100/60 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-100/40">
          <div>
            <h2 className="text-sm font-bold text-gray-100 uppercase tracking-widest">
              Keyboard Shortcuts
            </h2>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Navigate MetroPulse faster
            </p>
          </div>
          <button
            onClick={onClose}
            className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-500 hover:text-white hover:bg-dark-300/60 transition-all"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Shortcuts list */}
        <div className="p-5 space-y-5 max-h-[60vh] overflow-y-auto no-scrollbar">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.title}>
              <h3 className="text-[9px] font-bold uppercase tracking-widest text-gray-500 mb-2.5">
                {group.title}
              </h3>
              <div className="space-y-1.5">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.keys}
                    className="flex items-center justify-between py-1.5"
                  >
                    <span className="text-xs text-gray-300 font-medium">
                      {shortcut.description}
                    </span>
                    <kbd className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-dark-100/50 bg-dark-300/60 text-[10px] font-mono font-bold text-gray-300 shadow-sm">
                      {shortcut.keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-dark-100/30 p-4 text-center">
          <p className="text-[9px] text-gray-600 uppercase tracking-wider font-medium">
            Press <kbd className="px-1.5 py-0.5 rounded border border-dark-100/50 bg-dark-300/40 text-gray-400 font-mono font-bold">?</kbd> or <kbd className="px-1.5 py-0.5 rounded border border-dark-100/50 bg-dark-300/40 text-gray-400 font-mono font-bold">Esc</kbd> to close
          </p>
        </div>
      </div>
    </div>
  );
}

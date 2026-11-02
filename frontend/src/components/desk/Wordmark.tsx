/** The MetroPulse mark: a station roundel whose bar is a pulse trace. */
export function Mark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="16" r="12.5" fill="none" stroke="#D9480F" strokeWidth="5" />
      <rect x="0" y="12.5" width="32" height="7" fill="#1E3A8A" />
      <path
        d="M2 16 H10 L12.5 11 L16 21 L19 13.5 L20.5 16 H30"
        fill="none"
        stroke="#F4EFE6"
        strokeWidth="1.8"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Wordmark({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Mark size={size} />
      <span className="font-display text-xl font-bold tracking-tight">
        Metro<span className="text-signal">Pulse</span>
      </span>
    </span>
  );
}

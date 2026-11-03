"use client";

import Link from "next/link";
import { Wordmark } from "@/components/desk/Wordmark";

/**
 * If the desk ever throws, this keeps a way out: data loaded on this device is the only
 * state that survives a reload, so the recovery action clears it.
 */
export default function DeskError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const clearData = () => {
    try {
      const keys: string[] = [];
      for (let i = 0; i < window.localStorage.length; i++) {
        const k = window.localStorage.key(i);
        if (k && k.startsWith("metropulse.citydata.")) keys.push(k);
      }
      keys.forEach((k) => window.localStorage.removeItem(k));
    } catch {
      /* blocked storage: nothing to clear */
    }
    reset();
  };
  return (
    <div className="paper-grain flex min-h-screen flex-col items-center justify-center px-6 text-ink">
      <Wordmark />
      <h1 className="mt-6 font-display text-3xl font-bold">The desk hit an error</h1>
      <p className="mt-2 max-w-md text-center text-ink-soft">
        This usually means a file loaded under Your data could not be used. Clearing that data and trying again fixes it.
      </p>
      <p className="mt-2 max-w-md break-words text-center font-mono text-[11px] text-ink-faint">{error.message}</p>
      <div className="mt-6 flex gap-3">
        <button type="button" onClick={clearData} className="border-2 border-ink bg-ink px-4 py-2 font-semibold text-paper hover:bg-signal hover:border-signal">
          Clear my data and retry
        </button>
        <button type="button" onClick={reset} className="border-2 border-ink px-4 py-2 font-semibold hover:bg-paper-deep">
          Try again
        </button>
        <Link href="/" className="border-2 border-ink px-4 py-2 font-semibold hover:bg-paper-deep">
          Home
        </Link>
      </div>
    </div>
  );
}

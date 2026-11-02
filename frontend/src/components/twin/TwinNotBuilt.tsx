"use client";

/** True when an API error means the twin data has not been built on the backend yet. */
export function isNotBuiltError(message: string | null | undefined): boolean {
  return !!message && /twin data not built/i.test(message);
}

const STEPS: { title: string; body: string; code?: string }[] = [
  {
    title: "See which source files are missing",
    body: "Run this from the backend folder.",
    code: "python scripts/twin_build.py check",
  },
  {
    title: "Download them into data/twin/manual/",
    body:
      "Use the paths listed in data/twin/manual/README.md. LGD, Survey of India and VIIRS need a browser login, so this step is manual. DataMeet and Census 2011 are plain downloads.",
  },
  {
    title: "Build the twin",
    body: "Use the date of your LGD export as the boundary version.",
    code: "python scripts/twin_build.py build --boundary-version lgd-YYYYMMDD",
  },
  {
    title: "Reload this page",
    body: "The API picks up the new data without a restart.",
  },
];

export function TwinNotBuilt({ onDismiss }: { onDismiss?: () => void }) {
  return (
    <section
      role="alert"
      aria-labelledby="twin-not-built-title"
      className="absolute left-1/2 top-1/2 z-20 max-h-[calc(100%-6rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-slate-700 bg-slate-950/95 p-5 text-sm text-slate-300 shadow-xl max-sm:top-[4.5rem] max-sm:max-h-[calc(100%-15rem)] max-sm:translate-y-0 max-sm:p-4"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-amber-300">Setup needed</p>
      <h2 id="twin-not-built-title" className="mt-1 text-lg font-semibold text-slate-50">
        The map data hasn&apos;t been built yet
      </h2>
      <p className="mt-2 max-sm:hidden">
        District boundaries and indicators come from government sources that are built locally.
        The backend is running, but it has no built data to serve.
      </p>
      <ol className="mt-4 space-y-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="flex gap-3">
            <span
              aria-hidden="true"
              className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs text-slate-200"
            >
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-slate-100">{s.title}</p>
              <p className="mt-0.5 text-slate-400">{s.body}</p>
              {s.code && (
                <code className="mt-1.5 block whitespace-pre-wrap break-words rounded bg-slate-900 px-2 py-1.5 font-mono text-xs text-sky-200">
                  {s.code}
                </code>
              )}
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded bg-sky-600 px-3 py-1.5 font-medium text-white hover:bg-sky-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
        >
          Reload
        </button>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="rounded border border-slate-600 px-3 py-1.5 text-slate-200 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          >
            Hide
          </button>
        )}
      </div>
    </section>
  );
}

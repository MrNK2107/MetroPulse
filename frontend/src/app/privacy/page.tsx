import type { Metadata } from "next";
import Link from "next/link";
import { Wordmark } from "@/components/desk/Wordmark";

export const metadata: Metadata = {
  title: "Privacy · MetroPulse",
  description: "What MetroPulse keeps, where, and what it never sends.",
};

export default function PrivacyPage() {
  return (
    <div className="paper-grain min-h-screen text-ink">
      <nav className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <Wordmark />
        </Link>
      </nav>
      <main className="mx-auto max-w-3xl px-4 pb-16 sm:px-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">Privacy</p>
        <h1 className="mt-3 font-display text-4xl font-bold leading-tight">Privacy: what stays on your device</h1>
        <div className="mt-6 space-y-5 text-[15px] leading-relaxed">
          <section>
            <h2 className="font-display text-xl font-semibold">Your files</h2>
            <p className="mt-1 text-ink-soft">
              Boundaries, GTFS feeds and count files you load under Your data are parsed in your browser. Only the derived data (a
              boundary ring, a list of stations, daily counts per station) is kept, in your browser&rsquo;s <code>localStorage</code> on
              that device. Nothing is uploaded, and there is no upload endpoint. Remove it any time with Clear all in the drawer.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold">Saved lines</h2>
            <p className="mt-1 text-ink-soft">
              Lines you save live in the same browser store. A shared link carries the line&rsquo;s coordinates in the address itself,
              so whoever you send it to sees the line without anything being stored on a server.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold">Accounts and tracking</h2>
            <p className="mt-1 text-ink-soft">
              There are no accounts by default and no analytics. The desk does not set cookies. The web server sees the ordinary
              request logs any website sees. If the operator has enabled workspaces, you can choose to sign in with a magic link;
              then the lines you save are stored in that workspace under your email, and nothing else is. Files you load stay on
              your device either way.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold">The one exception</h2>
            <p className="mt-1 text-ink-soft">
              The optional planning agent sends your typed questions to a language-model provider chosen by whoever runs the backend.
              It is off by default and needs a token to reach; the desk never calls it on its own.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold">The API</h2>
            <p className="mt-1 text-ink-soft">
              The public <Link href="/developers" className="underline">JSON API</Link> serves only the sample city model. It never
              sees data you loaded on the desk.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}

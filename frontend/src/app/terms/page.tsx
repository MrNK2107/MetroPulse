import type { Metadata } from "next";
import Link from "next/link";
import { Wordmark } from "@/components/desk/Wordmark";

export const metadata: Metadata = {
  title: "Terms · MetroPulse",
  description: "Terms of use for the MetroPulse desk, API and optional workspaces.",
};

const SECTIONS: [string, string][] = [
  [
    "What this is",
    "MetroPulse is a planning desk. It computes indicative figures from a model and from files you load. It is a tool for exploring and framing a study, not a ridership forecast, an engineering estimate or professional advice.",
  ],
  [
    "Your data",
    "Files you load are parsed in your browser and stay on your device unless you sign in to a workspace, in which case the lines you save are stored in that workspace under your account. You keep all rights to your data. You confirm you may use the files you load.",
  ],
  [
    "The numbers",
    "Figures are provided as-is. Every number shows how it was computed; check the formula and the data note before citing one. We are not liable for decisions made on them.",
  ],
  [
    "Acceptable use",
    "Do not use the service to attack or overload it, to scrape it at a rate that degrades it for others, or to load data you are not allowed to process.",
  ],
  [
    "The API",
    "The public API serves the sample model, is provided as-is, may change with notice in the changelog, and may be rate-limited by the host.",
  ],
  [
    "Workspaces",
    "Workspaces are optional and in beta. Sign-in uses a magic link sent to your email. You can delete your lines at any time; deleting your account removes them.",
  ],
  ["Changes", "These terms may change. The date at the top of this page is the version. Material changes are noted in the changelog."],
];

export default function TermsPage() {
  return (
    <div className="paper-grain min-h-screen text-ink">
      <nav className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <Wordmark />
        </Link>
        <Link href="/privacy" className="text-sm underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
          Privacy
        </Link>
      </nav>
      <main className="mx-auto max-w-3xl px-4 pb-16 sm:px-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">Terms of use · draft of 2026-11-03</p>
        <h1 className="mt-3 font-display text-4xl font-bold leading-tight">Terms, in plain words</h1>
        <p className="mt-3 border-2 border-dashed border-ink p-3 text-sm text-ink-soft">
          This is a plain-language draft written for the people who use the desk. It has not been reviewed by counsel yet; the
          operator should have it reviewed before relying on it.
        </p>
        <div className="mt-6 space-y-5 text-[15px] leading-relaxed">
          {SECTIONS.map(([h, body]) => (
            <section key={h}>
              <h2 className="font-display text-xl font-semibold">{h}</h2>
              <p className="mt-1 text-ink-soft">{body}</p>
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}

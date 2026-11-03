import Link from "next/link";
import { getCity } from "@/lib/pulse/geo";
import { getCityModel } from "@/lib/pulse/model";
import { detectIncidents } from "@/lib/pulse/alerts";
import { Wordmark } from "@/components/desk/Wordmark";
import { HeroMap } from "@/components/landing/HeroMap";

const LOOP = [
  {
    verb: "See",
    name: "Pulse",
    title: "a 168-hour city playback",
    body: "Every hexagon in the city has a weekday and a weekend demand profile. Press play and watch the morning wave into the job hubs, the evening release and the quiet Sunday.",
  },
  {
    verb: "Notice",
    name: "Alerts",
    title: "alerts that explain themselves",
    body: "A robust detector compares this week with the same hour in the four weeks before it, joins flagged hexagons into incidents and writes each one up: what, where, how big, the likely cause and what to check.",
  },
  {
    verb: "Decide",
    name: "Siting",
    title: "what if a station opens here?",
    body: "Drop a pin, pick metro, BRT or feeder. Get residents and jobs in the walk band, daily boardings, how much is new coverage, the peak hour and a 0-100 score with its formula. Or ask for the three best sites.",
  },
  {
    verb: "Persuade",
    name: "Briefing",
    title: "a briefing a commissioner reads on a phone",
    body: "One click turns the week into an editorial, print-ready briefing: headline numbers, demand cores, walk-band coverage today and with the recommended sites, incidents and recommended sites, with methodology at the end. Save it as a PDF for the board pack.",
  },
];

const TRUST = [
  ["Explanations, not just anomalies", "Every alert carries a deterministic rule trace, so an engineer can audit why it fired."],
  ["Scores you can defend", "Siting shows the formula and its inputs. No black box in front of an appraisal committee."],
  ["Built for Indian planning", "NTOD walk bands, DPR alternatives analysis and briefings sized for how decisions actually circulate."],
  ["Runs on a laptop", "The core loop runs in the browser. No GPU, no language model, no map-tile subscription."],
];

const PLANS = [
  ["Explorer", "Free", "Students, journalists, evaluation", "All 30 sample cities, Pulse, Siting, watermarked briefings"],
  ["Desk", "₹3.5 lakh / city / yr", "Consultancies on a CMP or DPR", "Your data loaded, unlimited scenarios, unbranded briefings, exports, 3 seats"],
  ["Authority", "₹20-40 lakh / city / yr", "Metro corporations, UMTAs, SPVs", "Live feeds, alert routing, calibration against counts, SSO, on-prem, 25 seats"],
  ["API", "Usage-based", "Mobility operators, proptech", "Siting and catchment endpoints, embeddable map"],
];

export default function Landing() {
  const chennai = getCity("chennai")!;
  const top = detectIncidents(getCityModel(chennai))[0];

  return (
    <div className="paper-grain min-h-screen text-ink">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Wordmark />
        <div className="flex items-center gap-5 text-sm">
          <Link href="/brief?city=chennai" className="hidden hover:text-signal sm:inline">
            Sample briefing
          </Link>
          <Link href="/twin" className="hidden hover:text-signal sm:inline">
            India Twin
          </Link>
          <Link
            href="/desk?city=chennai"
            className="border-2 border-ink px-3 py-1.5 font-semibold hover:bg-ink hover:text-paper focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            Open the desk
          </Link>
        </div>
      </nav>

      <header className="mx-auto grid max-w-6xl items-center gap-8 px-4 pb-14 pt-6 sm:px-6 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">Mobility intelligence for Indian cities</p>
          <h1 className="mt-4 font-display text-5xl font-bold leading-[0.98] tracking-tight sm:text-6xl lg:text-7xl">
            Test the station before you pour the concrete.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-soft">
            MetroPulse shows where a city moves, hour by hour and hexagon by hexagon. It flags the hours that break pattern and
            says why, scores a proposed metro, BRT or feeder stop in seconds, and turns the week into a briefing.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/desk?city=chennai"
              className="border-2 border-ink bg-ink px-5 py-3 font-semibold text-paper shadow-[5px_5px_0_0_#D9480F] transition hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[3px_3px_0_0_#D9480F] focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
            >
              Open the desk
            </Link>
            <Link href="/brief?city=chennai" className="font-semibold underline decoration-signal decoration-2 underline-offset-4">
              Read a sample briefing
            </Link>
          </div>
          <p className="mt-6 font-mono text-[11px] text-ink-faint">30 Indian cities · runs offline · no sign-up</p>
        </div>
        <div className="aspect-square w-full border-2 border-ink bg-paper shadow-[8px_8px_0_0_#16130F]">
          <HeroMap />
        </div>
      </header>

      <section aria-labelledby="loop" className="border-y-2 border-ink bg-paper">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <h2 id="loop" className="max-w-2xl font-display text-3xl font-semibold leading-tight sm:text-4xl">
            One loop, run every week: see, notice, decide, persuade.
          </h2>
          <div className="mt-10 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {LOOP.map((s, k) => (
              <div key={s.verb} className="border-t-4 border-ink pt-3">
                <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">
                  0{k + 1} · {s.name}
                </div>
                <h3 className="mt-2 font-display text-2xl font-semibold leading-tight">
                  {s.verb}
                  <span className="text-signal">:</span> <span className="font-normal italic">{s.title}</span>
                </h3>
                <p className="mt-3 text-[15px] leading-relaxed text-ink-soft">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {top && (
        <section aria-labelledby="clipping" className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">From this week&rsquo;s feed, Chennai</p>
              <h2 id="clipping" className="mt-3 font-display text-3xl font-semibold leading-tight">
                A detector that can&rsquo;t say why gets ignored.
              </h2>
              <p className="mt-3 text-ink-soft">
                So every incident comes with its reasoning. This one was computed when this page was built, from the sample city
                model.
              </p>
            </div>
            <blockquote className="border-l-4 border-signal bg-paper-deep/60 p-5">
              <p className="font-display text-2xl font-semibold leading-snug">{top.headline}</p>
              <p className="mt-3 leading-relaxed">{top.explanation}</p>
              <p className="mt-2 leading-relaxed">
                <span className="font-semibold">Likely cause:</span> {top.likelyCause}
              </p>
              <p className="mt-2 leading-relaxed text-ink-soft">
                <span className="font-semibold text-ink">What to check:</span> {top.whatToCheck}
              </p>
              <ol className="mt-4 list-decimal space-y-0.5 border-t border-ink/20 pl-5 pt-3 font-mono text-[11px] text-ink-soft">
                {top.ruleTrace.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ol>
            </blockquote>
          </div>
        </section>
      )}

      <section aria-labelledby="trust" className="bg-ink text-paper">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <h2 id="trust" className="font-display text-3xl font-semibold">Why planners can trust it</h2>
          <dl className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {TRUST.map(([t, d]) => (
              <div key={t} className="border-t border-paper/30 pt-3">
                <dt className="font-display text-xl font-semibold">{t}</dt>
                <dd className="mt-2 text-[15px] leading-relaxed text-paper/75">{d}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section aria-labelledby="who" className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 id="who" className="font-display text-3xl font-semibold">Who it&rsquo;s for</h2>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div className="border-2 border-ink p-5">
            <h3 className="font-display text-xl font-semibold">Metro rail corporations and UMTAs</h3>
            <p className="mt-2 text-ink-soft">
              Pick station sites and feeder routes for the DPR, and defend the ridership numbers in front of the board and the
              appraisal committee.
            </p>
          </div>
          <div className="border-2 border-ink p-5">
            <h3 className="font-display text-xl font-semibold">Mobility consultancies</h3>
            <p className="mt-2 text-ink-soft">
              Do the first 80% of a demand study (zoning, catchments, option scoring) in days, then spend expert time on
              calibration.
            </p>
          </div>
        </div>
      </section>

      <section aria-labelledby="pricing" className="border-t-2 border-ink bg-paper">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <h2 id="pricing" className="font-display text-3xl font-semibold">Pricing</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {PLANS.map(([name, price, who, what], k) => (
              <div key={name} className={`border-2 p-5 ${k === 1 ? "border-signal bg-paper-deep/50" : "border-ink"}`}>
                <h3 className="font-display text-xl font-semibold">{name}</h3>
                <p className="mt-1 font-mono text-sm text-signal-deep">{price}</p>
                <p className="mt-3 text-sm font-medium">{who}</p>
                <p className="mt-1 text-sm text-ink-soft">{what}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="honesty" className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="border-2 border-dashed border-ink p-5">
          <h2 id="honesty" className="font-display text-xl font-semibold">About the numbers</h2>
          <p className="mt-2 max-w-3xl text-ink-soft">
            Pulse, Alerts, Siting and Briefings run on the <strong className="text-ink">sample city model</strong>: a seeded,
            synthetic demand field built from each city&rsquo;s real anchor points, published population and boundary, with
            scripted incidents so the detector has something to find. The algorithms are real. The numbers are illustrative until
            a city&rsquo;s own data (AFC taps, GTFS, survey zones) is connected.
          </p>
        </div>
      </section>

      <footer className="border-t-2 border-ink">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-6 text-sm sm:px-6">
          <Wordmark size={22} />
          <div className="flex gap-5">
            <Link href="/desk?city=chennai" className="hover:text-signal">
              Desk
            </Link>
            <Link href="/brief?city=chennai" className="hover:text-signal">
              Briefing
            </Link>
            <Link href="/twin" className="hover:text-signal">
              India Twin
            </Link>
            <Link href="/developers" className="hover:text-signal">
              Developers
            </Link>
            <Link href="/privacy" className="hover:text-signal">
              Privacy
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getCity, listCities } from "@/lib/pulse/geo";
import { getCityModel } from "@/lib/pulse/model";
import { citySummary, pct } from "@/lib/pulse/summary";
import { dayHourLabel, hourLabel } from "@/lib/pulse/time";
import { Wordmark } from "@/components/desk/Wordmark";
import { fmtInt } from "@/lib/pulse/format";

export const dynamicParams = false;

export function generateStaticParams() {
  return listCities().map((c) => ({ id: c.id }));
}

export function generateMetadata({ params }: { params: { id: string } }): Metadata {
  const city = getCity(params.id);
  if (!city) return { title: "City · MetroPulse" };
  const s = citySummary(getCityModel(city));
  return {
    title: `${s.name}: where the city moves · MetroPulse`,
    description: s.lede,
    openGraph: { title: s.headline, description: s.lede, type: "article" },
  };
}

const link = "border-2 border-ink px-3 py-1.5 text-sm font-semibold hover:bg-ink hover:text-paper focus:outline-none focus-visible:ring-2 focus-visible:ring-signal";

export default function CityPage({ params }: { params: { id: string } }) {
  const city = getCity(params.id);
  if (!city) notFound();
  const s = citySummary(getCityModel(city));
  const others = listCities().filter((c) => c.id !== city.id);

  return (
    <div className="paper-grain min-h-screen text-ink">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <Wordmark />
        </Link>
        <Link href={`/desk?city=${city.id}`} className={link}>
          Open the desk
        </Link>
      </nav>

      <main className="mx-auto max-w-5xl px-4 pb-16 sm:px-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">
          {city.state} · sample week · {fmtInt(city.population)} residents
        </p>
        <h1 className="mt-3 font-display text-4xl font-bold leading-[1.05] sm:text-5xl">{s.headline}</h1>
        <p className="mt-4 max-w-3xl text-lg leading-relaxed text-ink-soft">{s.lede}</p>

        <ul aria-label="Headline figures" className="mt-8 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          {[
            ["Residents", `${(s.population / 1e6).toFixed(1)}M`, "published city population"],
            ["Weekday trips", `${(s.dailyTrips / 1e6).toFixed(1)}M`, `peak hour ${hourLabel(s.peakHour)}`],
            ["Walk-band coverage", `${pct(s.coverageNow)} → ${pct(s.coverageAfter)}`, "today → with the 3 suggested sites"],
            ["Incidents", String(s.incidents.total), `${s.incidents.surges} surges · ${s.incidents.drops} drops`],
          ].map(([label, value, note]) => (
            <li key={label} className="border-t-2 border-ink pt-2">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">{label}</div>
              <div className="font-display text-3xl font-bold leading-tight tabular">{value}</div>
              <div className="text-xs text-ink-soft">{note}</div>
            </li>
          ))}
        </ul>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link href={`/desk?city=${city.id}`} className={`${link} bg-ink text-paper shadow-[4px_4px_0_0_#D9480F]`}>
            Open the desk
          </Link>
          <Link href={`/brief?city=${city.id}`} className={link}>
            Read the briefing
          </Link>
          <Link href={`/compare?city=${city.id}`} className={link}>
            Compare lines
          </Link>
          <a href={`/api/v1/cities/${city.id}`} className={link}>
            JSON
          </a>
        </div>

        <section aria-labelledby="city-incidents" className="mt-12">
          <h2 id="city-incidents" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            This week&apos;s incidents
          </h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            {s.topIncidents.map((i) => (
              <article key={i.id} className={`border-l-4 pl-3 ${i.kind === "surge" ? "border-signal" : "border-supply"}`}>
                <h3 className="font-display text-lg font-semibold leading-snug">{i.headline}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{i.explanation}</p>
                <p className="mt-1 text-sm">
                  <span className="font-semibold">Likely cause: </span>
                  {i.likelyCause}
                </p>
                <p className="mt-1 font-mono text-[11px] text-ink-faint">peak {dayHourLabel(i.peakHour)}</p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="city-sites" className="mt-12">
          <h2 id="city-sites" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            Recommended metro sites
          </h2>
          <p className="mt-2 text-sm text-ink-soft">
            Greedy search over every hexagon. Each site counts only demand that existing hubs and the sites above it do not already
            serve.
          </p>
          <ol className="mt-3 divide-y divide-ink/15">
            {s.suggested.map((site, k) => (
              <li key={site.name} className="flex items-baseline gap-3 py-2">
                <span className="font-display text-2xl font-bold text-supply">{k + 1}</span>
                <div className="flex-1">
                  <div className="font-medium">{site.name}</div>
                  <div className="font-mono text-[11px] text-ink-soft">
                    {fmtInt(site.newBoardings)} new boardings/day · peak {hourLabel(site.peakHour)} · score {site.score}
                  </div>
                </div>
                <Link href={`/desk?city=${city.id}&tab=siting&s=m.e.${site.lat},${site.lng}`} className="text-sm underline decoration-ink/40 underline-offset-2 hover:decoration-ink">
                  Open on the desk
                </Link>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="city-about" className="mt-12 border-2 border-dashed border-ink p-4 text-sm text-ink-soft">
          <h2 id="city-about" className="font-display text-lg font-semibold text-ink">
            About these numbers
          </h2>
          <p className="mt-1">
            This page is computed from the MetroPulse sample city model: a seeded synthetic demand field built from {city.name}&rsquo;s
            real anchor points and published population, with scripted incidents. The algorithms are real; the numbers are
            illustrative until the city&rsquo;s own data is loaded on the desk under Your data. Nothing here is a ridership forecast.
          </p>
        </section>

        <section aria-labelledby="city-others" className="mt-12">
          <h2 id="city-others" className="font-display text-lg font-semibold">
            Other cities
          </h2>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {others.map((c) => (
              <li key={c.id}>
                <Link href={`/city/${c.id}`} className="underline decoration-ink/30 underline-offset-2 hover:decoration-ink">
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}

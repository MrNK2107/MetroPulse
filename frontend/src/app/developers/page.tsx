import type { Metadata } from "next";
import Link from "next/link";
import { Wordmark } from "@/components/desk/Wordmark";

export const metadata: Metadata = {
  title: "Developers · MetroPulse API",
  description: "A public JSON API for the MetroPulse city model: cities, incidents, site scores, suggested sites and line scenarios.",
};

const BASE = "https://your-host.example";

const ENDPOINTS: { method: "GET" | "POST"; path: string; what: string; curl: string }[] = [
  {
    method: "GET",
    path: "/api/v1/cities",
    what: "The 30 sample cities: id, name, state, population, centre, metro flag.",
    curl: `curl ${BASE}/api/v1/cities`,
  },
  {
    method: "GET",
    path: "/api/v1/cities/{id}",
    what: "A city summary: headline, lede, weekday trips, peak hour, walk-band coverage now and with the three suggested sites, incident counts, the top three incidents and the suggested sites.",
    curl: `curl ${BASE}/api/v1/cities/chennai`,
  },
  {
    method: "GET",
    path: "/api/v1/cities/{id}/incidents",
    what: "This week's incidents, each with its explanation, likely cause, what to check and the rule trace.",
    curl: `curl ${BASE}/api/v1/cities/chennai/incidents`,
  },
  {
    method: "GET",
    path: "/api/v1/cities/{id}/site-score?lat=&lng=&mode=",
    what: "Score one station at a point (mode metro, brt or feeder): residents and jobs in the walk band, daily boardings, new share, peak hour, hourly profile, score and formula.",
    curl: `curl "${BASE}/api/v1/cities/chennai/site-score?lat=13.0418&lng=80.2341&mode=metro"`,
  },
  {
    method: "GET",
    path: "/api/v1/cities/{id}/suggest?mode=&k=",
    what: "The k best sites (1 to 5) from the greedy search, each counting only demand the earlier picks and existing hubs do not serve.",
    curl: `curl "${BASE}/api/v1/cities/chennai/suggest?mode=metro&k=3"`,
  },
  {
    method: "POST",
    path: "/api/v1/cities/{id}/scenario",
    what: "Evaluate a line: body { mode, alignment, stations: [{ lat, lng, name? }], costs? }. Returns per-station results, totals, length, spacing compliance, cost sketch and the network score.",
    curl: `curl -X POST ${BASE}/api/v1/cities/chennai/scenario -H "content-type: application/json" -d '{"mode":"metro","alignment":"elevated","stations":[{"lat":13.0418,"lng":80.2341},{"lat":13.0418,"lng":80.2452}]}'`,
  },
];

export default function DevelopersPage() {
  return (
    <div className="paper-grain min-h-screen text-ink">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="focus:outline-none focus-visible:ring-2 focus-visible:ring-signal">
          <Wordmark />
        </Link>
        <Link href="/desk?city=chennai" className="border-2 border-ink px-3 py-1.5 text-sm font-semibold hover:bg-ink hover:text-paper">
          Open the desk
        </Link>
      </nav>
      <main className="mx-auto max-w-5xl px-4 pb-16 sm:px-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">Developers</p>
        <h1 className="mt-3 font-display text-4xl font-bold leading-tight">The MetroPulse API, v1</h1>
        <p className="mt-4 max-w-3xl text-lg leading-relaxed text-ink-soft">
          The same model the desk runs in the browser, served as JSON. Every endpoint is read-only, cacheable for an hour and open to
          any origin. There is no key and no rate limit at this layer; the hosting platform&rsquo;s limits apply.
        </p>

        <section aria-labelledby="dev-envelope" className="mt-10">
          <h2 id="dev-envelope" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            The envelope
          </h2>
          <p className="mt-2 text-sm text-ink-soft">Every response, success or failure, has the same shape. Errors use HTTP 400 or 404.</p>
          <pre className="mt-3 overflow-x-auto bg-ink p-4 font-mono text-[12px] leading-relaxed text-paper">
            {`{ "success": true,  "data": { ... },  "error": null,                                   "meta": { "version": "v1", "model": "sample", ... } }
{ "success": false, "data": null,     "error": { "code": "city_not_found", "message": "..." }, "meta": { ... } }`}
          </pre>
        </section>

        <section aria-labelledby="dev-endpoints" className="mt-10">
          <h2 id="dev-endpoints" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            Endpoints
          </h2>
          <table aria-label="Endpoints" className="mt-3 w-full text-left text-sm">
            <thead>
              <tr className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
                <th className="py-1 pr-3 font-normal">Method</th>
                <th className="py-1 pr-3 font-normal">Path</th>
                <th className="py-1 font-normal">Returns</th>
              </tr>
            </thead>
            <tbody>
              {ENDPOINTS.map((e) => (
                <tr key={e.path} className="border-t border-ink/20 align-top">
                  <td className="py-2 pr-3 font-mono text-[12px] font-semibold">{e.method}</td>
                  <td className="py-2 pr-3 font-mono text-[12px]">{e.path}</td>
                  <td className="py-2 text-ink-soft">{e.what}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section aria-labelledby="dev-examples" className="mt-10">
          <h2 id="dev-examples" className="border-b-2 border-ink pb-1 font-display text-2xl font-semibold">
            Examples
          </h2>
          <div className="mt-3 space-y-3">
            {ENDPOINTS.map((e) => (
              <div key={e.path}>
                <div className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                  {e.method} {e.path}
                </div>
                <pre className="mt-1 overflow-x-auto bg-paper-deep p-3 font-mono text-[12px] leading-relaxed">{e.curl}</pre>
              </div>
            ))}
          </div>
          <p className="mt-3 text-sm text-ink-soft">Replace the host with wherever this app is deployed. On a local build it is http://localhost:3000.</p>
        </section>

        <section aria-labelledby="dev-caveat" className="mt-10 border-2 border-dashed border-ink p-4 text-sm text-ink-soft">
          <h2 id="dev-caveat" className="font-display text-lg font-semibold text-ink">
            About the numbers
          </h2>
          <p className="mt-1">
            The API serves the MetroPulse sample city model: a seeded synthetic demand field built from each city&rsquo;s real anchor
            points and published population, with scripted incidents. The algorithms are real; the numbers are illustrative. Data a
            user loads on the desk (boundary, stations, counts) stays in their browser and is not available through the API.
          </p>
        </section>
      </main>
    </div>
  );
}

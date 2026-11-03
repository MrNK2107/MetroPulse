# MetroPulse 2.0: from demo to desk

**Date:** 2026-11-03
**Status:** approved by the owner's standing grant of full authority (2026-11-03); calls below are the builder's
**Base:** `integrate/desk-on-main` (531a18c), branch `startup/2026-11-03`

## Intent

MetroPulse 1.x is a convincing demo: a demand-first planning desk for 30 Indian cities with a four-step loop
(see, notice, decide, persuade) that runs in the browser on a synthetic city model. Every screen says
"the numbers are illustrative until a city's own data is connected", and nothing lets anyone connect it.
A planner can score one station, but a DPR is about a line. Nothing they do is saved. The repo still
carries the retired simulator (dormant Python modules, a 25-day plan and a spec for a product that no
longer exists), and it has no licence.

2.0 closes those four gaps so that the product can be put in front of a consultancy or a metro
corporation and used on a real engagement, and so that the repository reads as a company's codebase
rather than a hackathon's.

## Goals

1. **Your data, in the browser.** A user can load a city boundary (GeoJSON), its stations (GTFS static
   zip or a stations CSV) and observed station counts (CSV). The desk then runs on their boundary and
   hubs, the siting numbers are calibrated against their counts, and every screen says what was loaded.
   Nothing leaves the browser.
2. **Lines, not stops.** A scenario is a named, ordered set of stations of one mode. The desk reports
   network boardings with mutual cannibalisation, walk-band coverage, line length, station spacing
   warnings, a sourced capital cost sketch and cost per boarding. Scenarios are saved locally, shareable
   by link, importable and exportable as JSON, and comparable side by side with an alternatives table
   formatted for a DPR.
3. **A public face per city and an API.** Thirty static city pages with the briefing headline, a sitemap,
   and a documented JSON API (cities, incidents, site score, suggestions) served by the Next.js app.
4. **A company-grade repository.** Dormant simulator code and stale documents removed, a licence, security
   and contribution policies, dependency updates, end-to-end tests in CI, ADRs for the decisions below,
   and a 2.0.0 release entry.

## Non-goals (this release)

- Accounts, organisations, cloud-saved scenarios, SSO. Local-first plus link sharing covers single-user
  use; workspaces are the first paid feature and come after a design partner asks for them.
- Live feeds (GTFS-RT, AFC streams), alert routing, a basemap. The loop stays deterministic and offline.
- Replacing the synthetic demand field with a real one. Calibration scales the model's outputs against
  observed counts; it does not rebuild the field from them. That is the next milestone and needs OD data.
- Per-user auth on `/ws/agent`. Unchanged; still the shared token.

## Anti-goals

- Numbers that cannot show their working. Every new figure (network score, cost, calibration factor)
  shows its formula and inputs, like the siting score does today.
- Uploaded data silently leaving the browser. No upload endpoint. The privacy page states this.
- A second product inside the repo. Nothing from the simulator comes back.

## Constraints

- The core loop stays plain TypeScript in `frontend/src/lib/pulse/`, runs client-side in about a second
  per city, and keeps server render and browser render bit-identical (the hex grid rounding rule).
- Hermetic tests: no test touches the network (existing guards in both suites stay).
- Jest locally with `--maxWorkers=2`; CI uses `npm run test:ci`.
- Keep the paper-and-ink identity (Fraunces, IBM Plex, newsprint ground, vermilion demand, indigo supply).
  New screens use the existing primitives; no new UI library.
- API envelope `{ success, data, error, meta }` for the new Next.js routes, matching the backend.

## Design

### 1. Your data (client-side import)

**Where it lives.** `frontend/src/lib/pulse/userdata.ts` defines

```ts
interface CityData {
  version: 1;
  cityId: string;
  boundary?: { source: string; ring: [number, number][] };                 // [lng, lat]
  hubs?: { source: string; stations: { name: string; lat: number; lng: number; mode: ModeId }[] };
  counts?: { source: string; rows: { station: string; dailyBoardings: number }[] };
  loadedAt: string; // ISO
}
```

stored in `localStorage` under `metropulse.citydata.<cityId>.v1` (derived data only; a GTFS zip of tens
of MB reduces to a few KB of stops). Reads and writes are wrapped in try/catch; a blocked store degrades
to in-memory for the session.

**Parsers** (`frontend/src/lib/pulse/import/`), each pure and unit-tested on fixtures:

- `geojson.ts`: accepts Feature, FeatureCollection, Polygon, MultiPolygon. Takes the largest outer ring
  by shoelace area, drops holes, re-closes it, rejects rings with fewer than 4 points or coordinates out
  of range. Returns the ring as `[lng, lat][]`.
- `gtfs.ts`: unzips with `fflate` (the one new dependency, about 8 kB), parses `stops.txt`, `routes.txt`,
  `trips.txt`, `stop_times.txt` with a small RFC 4180 CSV reader (quoted fields, CRLF, BOM). Stations are
  `location_type = 1` stops, or `0` stops with no parent, de-duplicated by name within 150 m. Mode comes
  from the route types serving the stop (`1` subway or `2` rail → metro, `3` bus → feeder, BRT not
  distinguishable from GTFS and left to the stations CSV). Stops more than 60 km from the city centre are
  dropped and counted in the report. If `stop_times.txt` is missing, every stop is `feeder` unless its
  name contains "metro" or "station".
- `stations-csv.ts`: columns `name, lat, lng, mode` (header names case-insensitive, synonyms `latitude`,
  `longitude`, `lon`, `type`). Mode defaults to metro.
- `counts-csv.ts`: columns `station, daily_boardings` or `station, date, boardings` (summed to a daily
  mean per station) or `station, hour, boardings` (summed per day). Station names are matched to loaded
  hubs case-insensitively after stripping "metro", "station", punctuation and extra spaces.

Every parser returns `{ ok: true, value, report: string[] } | { ok: false, error: string }` so the UI can
show what was kept and dropped.

**Model hooks.** `buildCityModel(city, data?: CityData)`:

- boundary replaces `city.boundary` before the grid is built (the cache key becomes `cityId` plus a hash
  of the data);
- hubs replace the city's `transport` anchors for coverage and for the hub demand term; the existing
  anchors of other types stay, so the demand field keeps its shape;
- `model.hubs` lists the stations with their mode so the map can draw them (metro square, bus dot).

`existingCoverage(model)` serves each hub with its own mode's walk band instead of the metro band for
all.

**Calibration** (`frontend/src/lib/pulse/calibrate.ts`). For each count row matched to a hub, modelled
daily boardings come from `scoreSite` at the hub. The calibration factor per mode is the median of
`observed / modelled` over that mode's matched stations (at least 3 stations, otherwise the mode is
"uncalibrated" and uses 1.0). The spread is the inter-quartile range of the ratios, reported as a ± band.
`scoreSite` multiplies boardings by the factor, and the formula line gains `× 0.83 (calibrated on 12
stations, IQR ±18%)`. The Data drawer shows the observed-versus-modelled table with per-station error.

**UI.** A "Your data" button in the desk header opens a drawer (`DataDrawer.tsx`) with three drop zones
(boundary, stations, counts), each showing the parser report, the current status, and a remove button;
a "Clear all" link; and an "Export data (JSON)" link that downloads the `CityData`. The yellow sample
banner is replaced, when data is loaded, by a status line listing what came from where
("Boundary: your GeoJSON · Stations: 142 from GTFS · Calibrated: metro on 12 stations"). Briefings carry
the same provenance sentence in their data note.

### 2. Scenarios: lines, not stops

**Model** (`frontend/src/lib/pulse/scenario.ts`):

```ts
interface Scenario {
  id: string;            // 8-char base32 slug
  cityId: string;
  name: string;
  mode: ModeId;
  alignment: "elevated" | "underground" | "at-grade";
  stations: { lat: number; lng: number; name?: string }[];  // in line order
  notes?: string;
  createdAt: string;
  updatedAt: string;
}
```

`evaluateScenario(model, scenario): NetworkResult` scores stations in order, each against coverage that
includes existing hubs and the earlier stations (the greedy-search rule), and returns per-station
results, totals (boardings, new boardings, residents and jobs in the union of walk bands), new walk-band
coverage share, line length (sum of straight segments; stations are not re-ordered), spacing warnings
(consecutive stations closer than 0.8 km or farther than 2.0 km for metro, 0.4 and 1.2 km for BRT and
feeder), capital cost and cost per daily boarding, and a network score with its formula.

**Cost sketch.** Assumptions live in one table with their source and are labelled as assumptions on
screen: elevated ₹250 crore/km, underground ₹600 crore/km, at-grade ₹120 crore/km, plus a per-station
cost of ₹60 crore (elevated), ₹250 crore (underground), ₹20 crore (at grade). These are 2024-era
order-of-magnitude figures from published Indian metro DPRs and MoHUA appraisals; the user can edit them
in the scenario panel and the edited values are saved with the scenario.

**Network score.** `score = 50 × min(1, boardings / (n × reference)) + 30 × new share + 20 × spacing
compliance`, where spacing compliance is the share of consecutive pairs inside the band. Shown with the
formula.

**Storage and sharing** (`frontend/src/lib/pulse/scenarioStore.ts`): a list in `localStorage`
(`metropulse.scenarios.v1`), with `list`, `save`, `remove`, `exportJson`, `importJson` (validates shape
and version). A scenario also encodes to a URL-safe string, `s=<mode>.<alignment>.<lat,lng;lat,lng…>`
with 4-decimal coordinates, so a link carries the line without any storage. The desk reads `?scenario=<id>`
(local library) or `?s=<encoded>` (shared link).

**UI.** The Siting tab gains a "Line" mode: pins accumulate in order, the map draws the polyline and
every station's walk band, the panel shows the network result with the per-station list (reorder by
drag is out of scope; up/down buttons), the cost table, and Save / Copy link / Add to compare.
"Suggest 3 sites" becomes "Suggest a line": the greedy picks are loaded as a scenario. A "Scenarios"
list in the panel opens, renames or deletes saved ones.

**Compare** (`/compare?city=<id>&a=<enc|id>&b=<enc|id>`): two columns and a delta column over the
network metrics, two small maps, and "Download alternatives table" as CSV and as Markdown (the format a
DPR alternatives-analysis annex uses: option, stations, length, boardings, coverage, cost, cost per
boarding, score).

**Briefing.** `/brief?city=<id>&s=<enc>` adds a "Proposed line" section with the per-station table and
cost sketch in place of the three suggested sites.

### 3. Public face and API

- `/city/[id]` (`generateStaticParams` over the 30 cities, `dynamicParams = false`): the briefing
  headline and lede, four headline figures, the top three incidents, the three suggested metro sites,
  and links to the desk, the briefing and the compare page. Each page sets `title`, `description` and
  Open Graph tags; `opengraph-image.tsx` renders a text card in the house style with `ImageResponse`.
- `app/sitemap.ts` and `app/robots.ts`.
- `/api/v1/*` route handlers, all GET, `Cache-Control: public, max-age=3600`, open CORS:
  - `GET /api/v1/cities` → id, name, state, population, centre, metro flag
  - `GET /api/v1/cities/{id}` → the briefing summary numbers
  - `GET /api/v1/cities/{id}/incidents` → this week's incidents
  - `GET /api/v1/cities/{id}/site-score?lat=&lng=&mode=` → `SiteResult` without the cell lists
  - `GET /api/v1/cities/{id}/suggest?mode=&k=` → suggestions (k ≤ 5)
  - `POST /api/v1/cities/{id}/scenario` with a `Scenario` body → `NetworkResult`
  Errors are `{ success: false, error: { code, message } }` with 400 or 404. Unknown routes under
  `/api/v1` return a 404 envelope. There is no rate limit at this layer; the hosting platform's limit
  applies (noted in the docs page).
- `/developers`: one page documenting the endpoints with curl examples, the envelope, and the data caveat.

### 4. Repository

**Delete** (with their tests): `backend/app/rag/`, `app/source_ingestion.py`, `app/core/`,
`app/simulation/explainability.py`, `app/simulation/overlay.py`, `app/simulation/confidence.py`,
`engine/grid.py`, `engine/prediction_generator.py`, `engine/scenario_parser.py`,
`engine/simulation_explainability.py`, `engine/translator.py`, `engine/confidence.py`,
`engine/provenance.py`, `engine/nl_engine/conversation.py`, `engine/nl_engine/group_scorer.py`, and the
unused classes in `engine/models.py` once nothing imports them. `app/simulation/llm.py` moves to
`app/llm.py` and the `app/simulation` package goes. Root `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `status.md`,
`docs/INDIA_OVERHAUL_PLAN.md`, `docs/RAG_ENGINE.md` and the May 2026 specs and plans move to
`docs/archive/` with a one-paragraph index saying what they were. `NIGHT_RUN_NOTES.md` moves to
`docs/archive/night-runs.md`.

**Add**: `LICENSE` (Apache-2.0; builder's call, see NEEDS_INPUT), `SECURITY.md` (reporting address,
supported versions, the token model), `CONTRIBUTING.md`, `.github/CODEOWNERS`, `.github/dependabot.yml`
(npm, pip, actions, weekly), issue and PR templates, `docs/adr/` with four records (browser-first core
loop; client-side data import; simulator removal; API in the Next.js app), a `/privacy` page, and a
Playwright smoke suite (`frontend/e2e/`: landing, desk tabs, line scenario, compare, brief, city page,
API) run in CI against `next build && next start`.

**Versions**: frontend and backend to 2.0.0; `CHANGELOG.md` gets a `2.0.0` section; README, PRODUCT.md,
ARCHITECTURE.md, SETUP.md and LIMITATIONS.md updated to match.

## Left to the builder

- Exact drawer layout and copy, within the identity above.
- The hash used for the model cache key and the slug alphabet.
- Fixture GTFS content (synthetic, a dozen stops; not copied from a real feed).
- Whether the OG image needs the city outline (text card is enough if it costs build time).

## Decisions only the owner can make (recorded in NEEDS_INPUT.md)

- Licence: Apache-2.0 chosen; swap if the company wants source-available or proprietary.
- Pricing tiers on the landing page: unchanged in substance, wording updated for 2.0.
- Terms of service: not written. The privacy page is factual; terms need counsel.

# Changelog

All notable changes to MetroPulse are documented here. Format follows [Conventional Changelog](https://www.conventionalcommits.org/).

## [2.2.0] - 2026-11-03

### Added
- **Team workspaces (beta)**: create a workspace, invite colleagues by email as editor or viewer,
  switch the desk's library between Personal and a workspace. Lines saved in a workspace sync to
  every member; viewers cannot save. Enforced by row-level security
  (`supabase/migrations/011_workspaces.sql`, with a `workspace_role()` helper).
- **Counts by hour shape the day**: a `station, hour, boardings` counts file now also gives the
  weekday demand its observed hourly profile (each cell keeps its daily total; weekends keep the
  model's shape).

## [2.1.0] - 2026-11-03

### Added
- **Zones** in Your data: a survey-zone CSV replaces the synthetic residents and jobs with the city's
  own totals, spread around each zone centroid.
- **Workspaces (beta)**: with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` set, magic-link
  sign-in and two-way sync of saved lines to a `scenarios` table under row-level security
  (`supabase/migrations/010_scenarios.sql`). Local-only without them.
- **Suggest a corridor**: a spacing-constrained suggestion that builds a line, not a hub network.
- `/terms` (plain-language draft), `app/desk/error.tsx` recovery page.

### Changed
- GTFS feeds are parsed in a Web Worker with an inline fallback; only the four needed files are
  inflated and `stop_times.txt` is scanned line by line.
- Boundaries are thinned to 5,000 vertices and must cover 5 to 10,000 km²; a stored boundary that
  cannot build a grid is dropped instead of breaking the desk.
- The API rejects prototype keys as modes, null bodies and partial cost tables.
- Store reads prefer the in-memory copy only after a failed write; saved lines are scoped to a city.
- `SECURITY.md` points at GitHub private vulnerability reporting.

## [2.0.0] - 2026-11-03

From demo to desk. The loop (see, notice, decide, persuade) now runs on a city's own data, builds
lines rather than single stops, compares alternatives, and has a public face per city plus a JSON
API. Spec: `docs/superpowers/specs/2026-11-03-startup-grade-design.md`.

### Added
- **Your data** (desk header): load a GeoJSON boundary, stations from a GTFS static zip or a CSV,
  and observed daily counts as a CSV. Files are parsed in the browser and only derived data is kept
  in `localStorage`; nothing is uploaded. The banner states what was loaded and from where.
- **Calibration**: with three or more matched stations per mode, siting boardings are scaled by the
  median observed/modelled ratio, with the inter-quartile spread shown as a ± band in the formula.
- **Line mode** on Siting: stations accumulate into an ordered line; network boardings net of the
  line's own cannibalisation, union walk-band coverage, length, spacing warnings against a per-mode
  band, an editable capital-cost sketch with its source, cost per daily boarding, and a network
  score with its formula. "Suggest a line" loads the three greedy picks.
- **Scenario library**: save, rename, open and delete lines on this device; JSON export and import;
  self-contained share links (`/desk?city=&s=`) that carry the line in the URL.
- **Compare** (`/compare`): two lines side by side with a signed delta column and a DPR alternatives
  table downloadable as CSV or Markdown.
- **Briefing with a proposed line** (`/brief?city=&s=`): the per-station table and cost sketch
  replace the recommended sites.
- **City pages** (`/city/{id}`, 30 static pages) with Open Graph cards, a sitemap and robots rules.
- **JSON API v1** (`/api/v1/*`): cities, city summary, incidents, site score, suggestions and a POST
  scenario evaluator, all in the `{ success, data, error, meta }` envelope, cacheable and open to
  any origin. Documented at `/developers`.
- `/privacy` page; Playwright smoke suite (`npm run e2e`) run in CI against the production build.
- Repository files: Apache-2.0 `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, CODEOWNERS, Dependabot,
  issue and PR templates, ADRs in `docs/adr/`, `NEEDS_INPUT.md` for owner decisions.

### Changed
- The city model takes the user's boundary and stations (`getCityModel(city, data)`); without data
  every 1.x number is unchanged (pinned by tests).
- Existing coverage serves each hub with its own mode's walk band.
- `placeName`, `fmtInt` and the hour-of-week helpers moved into `frontend/src/lib/pulse/` so server
  pages and the API can use them.

### Removed
- The retired simulator's dormant backend modules (`app/rag`, `app/simulation`, `engine/grid.py`,
  the translator, prediction generator, scenario parser and friends) and their tests.
  `app/llm.py` replaces `app/simulation/llm.py`. The May 2026 spec, plan and status documents moved
  to `docs/archive/`.

## [Unreleased]

### The mobility desk replaces the simulator
- `/desk` (Pulse, Alerts, Siting), `/brief` (printable city briefing), `/twin` (India twin) and the token-gated `/ws/agent` replace the simulator UI, `/ws/simulate` and `/api/simulations`.
- The June 2026 simulator-era work was merged in, not discarded. Features that still apply were ported to the desk; the rest went with the simulator.

### feat(desk)
- Keyboard shortcuts (Space, arrows, 1/2/3, J/K, L, E, B, Esc) and a `?` help dialog with a focus trap.
- "Copy link" for the current view (the URL already encodes city, tab, incident and suggested sites).
- Download this week's incidents as CSV.
- Busiest hexagons show a 24-hour sparkline and a trend against the four-week baseline.
- Installable PWA: web manifest, and a production-only service worker that keeps the desk working offline.
- A4 print stylesheet for the briefing: colours kept, sections not split across pages.

### feat(api)
- `X-Request-ID` correlation IDs on every response, and JSON request logs (no request bodies).
- Per-IP rate limit, `RATE_LIMIT_PER_MINUTE` (default 240, 0 disables). `POST /api/ingest` also keeps its own 3/min limit.
- `GET /api/health/llm` reports which providers have credentials, without calling them.
- Case studies: `year_from` / `year_to` filters and pagination.
- CORS origin validation at startup, and a size cap on the connector response cache.
- Routes stay under `/api`. The June `/api/v1` prefix was not adopted.

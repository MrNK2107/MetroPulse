# Changelog

All notable changes to MetroPulse are documented here. Format follows [Conventional Changelog](https://www.conventionalcommits.org/).

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

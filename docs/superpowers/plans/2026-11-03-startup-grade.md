# MetroPulse 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 1.x demo desk into a product a consultancy can use on a real engagement: own data in the browser, line scenarios with compare, public city pages and an API, and a company-grade repository.

**Architecture:** All product logic stays in pure TypeScript under `frontend/src/lib/pulse/` (parsers, model hooks, calibration, scenarios, summaries) with React components in `frontend/src/components/` and thin Next.js pages and route handlers under `frontend/src/app/`. The Python backend loses its dormant simulator modules and keeps the twin API and the agent socket. Nothing uploaded leaves the browser.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript strict, Tailwind 3, Jest + Testing Library, `fflate` (new, zip), Playwright (new, e2e), FastAPI + pytest.

**Spec:** `docs/superpowers/specs/2026-11-03-startup-grade-design.md`

## Global Constraints

- Core loop stays client-side, deterministic, bit-identical between server and browser render (the grid's rounded projection constant).
- No test touches the network (backend `conftest.py` guard; frontend `jest.setup.js` guard). Run Jest locally with `--maxWorkers=2`.
- Identity: paper `#F4EFE6`, ink `#16130F`, signal `#D9480F` (demand), supply `#1E3A8A`; Fraunces, IBM Plex Sans, IBM Plex Mono. Existing Tailwind tokens `paper`, `ink`, `signal`, `supply`.
- New API routes use the envelope `{ success, data, error, meta }`.
- One new runtime dependency only: `fflate`. Playwright is a dev dependency.
- Every new number on screen shows its formula or its inputs.
- Commits: `type(scope): description`.

## Review Focus

1. A GeoJSON whose largest polygon is far from the city (wrong file) must be rejected, not silently turned into an empty grid. Test in Task 4: ring centroid farther than 150 km from the city centre → `{ ok: false }`.
2. A GTFS zip with CRLF line endings, a UTF-8 BOM and quoted commas in stop names must parse the same as a clean one. Test in Task 3 (CSV reader) and Task 5.
3. Counts whose station names do not match any hub must be reported, not dropped silently, and a mode with fewer than 3 matches must stay uncalibrated. Tests in Tasks 6 and 9.
4. `localStorage` that throws (private mode, quota) must leave the desk usable. Tests in Tasks 7 and 12 with a throwing storage stub.
5. A shared `?s=` string that is malformed or references another city must open the desk with no scenario and a notice, never crash the server render. Test in Task 11 (`decodeScenario` returns null) and Task 13 (desk renders with a bad `s`).

---

## Phase A: repository hygiene

### Task 1: Remove the dormant simulator modules from the backend

**Files:**
- Delete: `backend/app/rag/` (whole package), `backend/app/source_ingestion.py`, `backend/app/core/` (whole package), `backend/app/simulation/` (whole package, after the move below), `backend/engine/grid.py`, `backend/engine/prediction_generator.py`, `backend/engine/scenario_parser.py`, `backend/engine/simulation_explainability.py`, `backend/engine/translator.py`, `backend/engine/confidence.py`, `backend/engine/provenance.py`, `backend/engine/nl_engine/conversation.py`, `backend/engine/nl_engine/group_scorer.py`
- Delete tests: `backend/tests/unit/test_conversation.py`, `test_credibility_system.py`, `test_grid.py`, `test_group_scorer.py`, `test_prediction_generator.py`, `test_provenance.py`, `test_rag_retriever.py`, `test_scenario_parser.py`, `test_source_ingestion.py`, `test_translator.py`, `test_translator_edge_cases.py`
- Move: `backend/app/simulation/llm.py` → `backend/app/llm.py`
- Modify: `backend/app/ws/agent.py:26` (`from app.llm import call_llm`), `backend/tests/unit/test_llm_call.py:11` (`from app import llm`), `backend/engine/models.py` (drop `SectorPrediction`, `Prediction`, `SimulationParams`, `GridState`, `HexCellState`, `AggregateMetrics`, `SimulationFrame`, `StartScenarioMessage`, `InputResponseMessage`, `PIPELINE_STAGES`, `N_SECTORS` if unused after deletion; keep `SECTOR_NAMES`, `SECTOR_LABELS`, `ParsedScenario`, `CityProfile`, `CaseStudy`, `CaseStudyMatchContext`, `CaseRetrievalAudit`), `backend/engine/nl_engine/__init__.py` and `backend/engine/__init__.py` (drop re-exports of deleted names), `backend/pyproject.toml` (version `2.0.0`), `docs/ARCHITECTURE.md` (remove the Dormant code section and the `app/simulation/llm.py` path)

**Interfaces:**
- Produces: `app.llm.call_llm` at the same signature as before.

- [ ] **Step 1: Write the guard test** in `backend/tests/unit/test_no_simulator.py`:

```python
import importlib, pathlib, pytest
BACKEND = pathlib.Path(__file__).resolve().parents[2]

@pytest.mark.parametrize("rel", ["app/rag", "app/simulation", "app/core", "app/source_ingestion.py",
    "engine/grid.py", "engine/prediction_generator.py", "engine/scenario_parser.py",
    "engine/simulation_explainability.py", "engine/translator.py", "engine/confidence.py",
    "engine/provenance.py", "engine/nl_engine/conversation.py", "engine/nl_engine/group_scorer.py"])
def test_simulator_module_is_gone(rel):
    assert not (BACKEND / rel).exists()

def test_llm_lives_in_app_llm():
    assert hasattr(importlib.import_module("app.llm"), "call_llm")

def test_models_keep_only_live_types():
    import engine.models as m
    for gone in ["SimulationParams", "GridState", "AggregateMetrics", "SimulationFrame", "Prediction"]:
        assert not hasattr(m, gone)
```

- [ ] **Step 2: Run it to see it fail**: `cd backend && .venv/Scripts/python -m pytest tests/unit/test_no_simulator.py -q` → FAIL (paths exist).
- [ ] **Step 3: Delete the files and tests listed, `git mv` llm.py, fix the two imports, trim `engine/models.py` and the package `__init__` files.** Use `grep -rn` for each deleted name across `backend/app backend/engine backend/scripts backend/tests` to find stragglers.
- [ ] **Step 4: Run the whole backend suite**: `.venv/Scripts/python -m pytest tests/unit tests/integration -q` → all pass (expect roughly 999 minus the deleted files' tests plus 16).
- [ ] **Step 5: Smoke import**: `.venv/Scripts/python -c "import app.main"` → no error.
- [ ] **Step 6: Update `docs/ARCHITECTURE.md`** (remove Dormant code section, fix the LLM row, note `engine/nl_engine` is used only by the agent's scenario parser) and bump `pyproject.toml` version.
- [ ] **Step 7: Commit** `refactor(backend): remove the retired simulator modules; app.llm replaces app.simulation.llm`.

### Task 2: Archive stale documents and add the company files

**Files:**
- Move: `SPEC.md` → `docs/archive/2026-05-spec-simulator.md`, `IMPLEMENTATION_PLAN.md` → `docs/archive/2026-05-implementation-plan-simulator.md`, `status.md` → `docs/archive/2026-10-status.md`, `NIGHT_RUN_NOTES.md` → `docs/archive/night-runs.md`, `docs/INDIA_OVERHAUL_PLAN.md` → `docs/archive/`, `docs/RAG_ENGINE.md` → `docs/archive/`, `docs/superpowers/specs/2026-05-26-scenario-driven-simulation-design.md`, `docs/superpowers/specs/2026-05-28-nl-simulation-design.md`, `docs/superpowers/plans/2026-05-28-nl-simulation.md` → `docs/archive/`
- Create: `docs/archive/README.md` (one paragraph per file: what it was, why it is archived), `LICENSE` (Apache-2.0, copyright "2026 MetroPulse contributors"), `SECURITY.md`, `CONTRIBUTING.md`, `.github/CODEOWNERS` (`* @MrNK2107`), `.github/dependabot.yml` (npm in `/frontend`, pip in `/backend`, github-actions, weekly), `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `docs/adr/0001-browser-first-core-loop.md`, `docs/adr/0002-client-side-data-import.md`, `docs/adr/0003-remove-the-simulator.md`, `docs/adr/0004-public-api-in-the-nextjs-app.md`, `NEEDS_INPUT.md` (licence, pricing wording, terms of service)
- Modify: `AGENTS.md` (drop the "parked for M2" line's references to deleted modules; add the new frontend folders once they exist, done again in Task 20), `README.md` references to the moved files

**Interfaces:** none.

- [ ] **Step 1: Write a repo-shape test** in `backend/tests/unit/test_repo_shape.py` asserting `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `.github/dependabot.yml`, `docs/adr/0001-browser-first-core-loop.md` exist at the repo root and `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `status.md`, `NIGHT_RUN_NOTES.md` do not.
- [ ] **Step 2: Run it** → FAIL.
- [ ] **Step 3: Make the moves with `git mv`, write the new files.** ADRs use the format: Context, Decision, Consequences, each under 300 words. SECURITY.md names the reporting address `security@metropulse.in` (placeholder flagged in NEEDS_INPUT), the supported version (2.x), and the token model (`AGENT_WS_TOKEN`, `INGEST_TOKEN`).
- [ ] **Step 4: Run the test** → PASS. `grep -rn "SPEC.md\|IMPLEMENTATION_PLAN\|NIGHT_RUN_NOTES\|status.md" README.md AGENTS.md SETUP.md docs/*.md` → only archive references remain.
- [ ] **Step 5: Commit** `chore(repo): licence, security and contribution policies, ADRs; archive simulator-era documents`.

## Phase B: your data

### Task 3: CSV reader and stations CSV parser

**Files:**
- Create: `frontend/src/lib/pulse/import/csv.ts`, `frontend/src/lib/pulse/import/stations.ts`, `frontend/src/lib/pulse/import/types.ts`
- Test: `frontend/src/lib/pulse/import/csv.test.ts`, `frontend/src/lib/pulse/import/stations.test.ts`

**Interfaces:**
- Produces (`types.ts`): `type ParseResult<T> = { ok: true; value: T; report: string[] } | { ok: false; error: string }`; `interface Station { name: string; lat: number; lng: number; mode: ModeId }`.
- Produces (`csv.ts`): `parseCsv(text: string): { header: string[]; rows: string[][] }` (RFC 4180: quoted fields with doubled quotes, CRLF and LF, leading BOM stripped, header lower-cased and trimmed, blank lines skipped); `findColumn(header: string[], names: string[]): number` (first match, -1 if none).
- Produces (`stations.ts`): `parseStationsCsv(text: string): ParseResult<Station[]>`; column synonyms `name|station|stop_name`, `lat|latitude`, `lng|lon|long|longitude`, `mode|type` (values `metro|brt|feeder|bus` where `bus` → `feeder`; missing → `metro`).

- [ ] **Step 1: Write tests** covering: BOM + CRLF + quoted comma field; doubled quotes; blank line; `findColumn` synonym; stations with `latitude/longitude` headers; missing lat column → `ok: false` with error naming the column; a row with non-numeric lat → skipped and reported, others kept.
- [ ] **Step 2: Run** `npx jest src/lib/pulse/import --maxWorkers=2` → FAIL.
- [ ] **Step 3: Implement.** Parser is a single-pass state machine over characters.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(import): CSV reader and stations CSV parser`.

### Task 4: GeoJSON boundary parser

**Files:**
- Create: `frontend/src/lib/pulse/import/geojson.ts`
- Test: `frontend/src/lib/pulse/import/geojson.test.ts`

**Interfaces:**
- Produces: `parseBoundaryGeoJson(text: string, centre: [number, number]): ParseResult<[number, number][]>` (ring as `[lng, lat]`, closed, outer ring of the largest polygon by shoelace area; accepts Polygon, MultiPolygon, Feature, FeatureCollection; rejects invalid JSON, fewer than 4 points, coordinates outside lng ±180 / lat ±90, or a ring centroid more than 150 km from `centre` with error "This boundary is about N km from <city centre>"); `ringAreaKm2(ring)` exported for the report line "Boundary: 612 km², 84 vertices".

- [ ] **Step 1: Write tests**: FeatureCollection with two polygons → the larger one; MultiPolygon → largest part; holes dropped; unclosed ring closed; 3-point ring → error; far-away ring → error with km; invalid JSON → error.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(import): GeoJSON boundary parser`.

### Task 5: GTFS static parser

**Files:**
- Create: `frontend/src/lib/pulse/import/gtfs.ts`, fixture builder `frontend/src/lib/pulse/import/__fixtures__/gtfs.ts` (builds a zip in-memory with `fflate.zipSync` from string tables; 12 synthetic stops around a given centre, 2 routes: one `route_type=1`, one `route_type=3`)
- Modify: `frontend/package.json` (add `fflate` `^0.8.2`)
- Test: `frontend/src/lib/pulse/import/gtfs.test.ts`

**Interfaces:**
- Produces: `parseGtfsZip(bytes: Uint8Array, centre: [number, number]): ParseResult<Station[]>`.
  Rules: stations = stops with `location_type=1`, plus `location_type` 0/blank stops with no `parent_station`; de-duplicate by normalised name within 150 m (keep the first); mode from the `route_type`s of routes whose trips stop there (`1`,`2` → `metro`; `3` → `feeder`; metro wins when both), via `stop_times.txt` → `trips.txt` → `routes.txt`; when `stop_times.txt` is absent, `metro` if the name matches `/metro|station/i` else `feeder`; drop stops farther than 60 km from `centre` and report the count; error when `stops.txt` is missing or the zip is unreadable.

- [ ] **Step 1: Write tests**: fixture → 12 stations, modes by route type; drop far stop and report "1 stop more than 60 km from the centre dropped"; no `stop_times.txt` → name rule; missing `stops.txt` → error; not a zip → error; name de-dup within 150 m.
- [ ] **Step 2: `npm i fflate@^0.8.2`** then run → FAIL. **Step 3: Implement** using `fflate.unzipSync` and `parseCsv`. **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(import): GTFS static zip to stations (fflate)`.

### Task 6: Counts CSV parser

**Files:**
- Create: `frontend/src/lib/pulse/import/counts.ts`
- Test: `frontend/src/lib/pulse/import/counts.test.ts`

**Interfaces:**
- Produces: `parseCountsCsv(text: string): ParseResult<{ station: string; dailyBoardings: number }[]>`; accepted shapes: `station,daily_boardings`; `station,date,boardings` (mean per station over dates); `station,hour,boardings` (sum over hours = one day); synonyms `stop|stop_name|name` for station, `boardings|riders|entries|taps` for the value. `normaliseStationName(name: string): string` exported: lower-case, strip the words `metro`, `station`, `stn`, punctuation, collapse spaces.

- [ ] **Step 1: Write tests** for the three shapes, synonym headers, non-numeric rows reported and skipped, `normaliseStationName("M.G. Road Metro Station") === "mg road"`.
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(import): station counts CSV parser`.

### Task 7: City data store

**Files:**
- Create: `frontend/src/lib/pulse/userdata.ts`
- Test: `frontend/src/lib/pulse/userdata.test.ts`

**Interfaces:**
- Produces: `interface CityData { version: 1; cityId: string; boundary?: { source: string; ring: [number, number][] }; hubs?: { source: string; stations: Station[] }; counts?: { source: string; rows: { station: string; dailyBoardings: number }[] }; loadedAt: string }`; `loadCityData(cityId: string): CityData | null`; `saveCityData(data: CityData): void`; `clearCityData(cityId: string): void`; `cityDataKey(data: CityData | null): string` (stable short hash of the JSON, `""` for null; FNV-1a hex); `describeCityData(data: CityData | null): string` (the status line: "Boundary: your GeoJSON · Stations: 142 from GTFS · Counts: 12 stations"); storage key `metropulse.citydata.<cityId>.v1`; a `Storage` that throws falls back to a module-level `Map` for the session.

- [ ] **Step 1: Write tests**: round trip; `version !== 1` or `cityId` mismatch → null; throwing `localStorage` (stub `getItem` to throw) → save then load still works in memory; `cityDataKey` stable across key order; `describeCityData`.
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(desk): local store for a city's own data`.

### Task 8: Model hooks for user data

**Files:**
- Modify: `frontend/src/lib/pulse/model.ts` (`buildCityModel(city, data?)`, `getCityModel(city, data?)` keyed by `city.id + ":" + cityDataKey(data)`, new `CityModel.hubs: Station[]` and `CityModel.data: CityData | null`), `frontend/src/lib/pulse/siting.ts` (`existingCoverage` serves each hub with `MODES[hub.mode].walkKm`), `frontend/src/components/desk/HexMap.tsx` (draw `hubs` prop: metro as the existing square, feeder/BRT as a small dot; `anchors` of type `transport` are not drawn when `hubs` is given)
- Test: `frontend/src/lib/pulse/model.test.ts`, `frontend/src/lib/pulse/siting.test.ts`

**Interfaces:**
- Consumes: `CityData`, `Station`, `cityDataKey`.
- Produces: `getCityModel(city: City, data?: CityData | null): CityModel`; `CityModel.hubs`; `CityModel.data`.
- Rule: without data, `hubs` = the city's `transport` anchors as `metro` stations, so every existing number is unchanged (pin this with a test comparing `dailyTrips` sums before and after the change for Chennai).

- [ ] **Step 1: Write tests**: model with a custom boundary has a different cell count and `model.data` set; hubs from data replace transport anchors in `hubs` and in `existingCoverage` (feeder hub covers a smaller band than a metro hub); the no-data model equals the 1.x model (sum of `dailyTrips` equals the recorded value, compute it once and hard-code).
- [ ] **Step 2–4: fail, implement, pass.** Keep `buildCityModel(city)` deterministic: the hub demand term uses `hubs` positions.
- [ ] **Step 5: Commit** `feat(model): city model takes the user's boundary and stations`.

### Task 9: Calibration

**Files:**
- Create: `frontend/src/lib/pulse/calibrate.ts`
- Modify: `frontend/src/lib/pulse/siting.ts` (`scoreSite(model, site, modeId, covered?, calibration?)` multiplies `dailyBoardings`, `newBoardings`, `hourly` by `calibration.factor[mode]` and appends ` × ${factor.toFixed(2)} (calibrated on ${n} stations, IQR ±${pct}%)` to `formula` when the mode is calibrated), `frontend/src/lib/pulse/model.ts` (`CityModel.calibration: Calibration` computed in `buildCityModel` when `data.counts` and `hubs` exist)
- Test: `frontend/src/lib/pulse/calibrate.test.ts`

**Interfaces:**
- Produces: `interface Calibration { factor: Record<ModeId, number>; stations: Record<ModeId, number>; iqr: Record<ModeId, number>; matched: { station: string; mode: ModeId; observed: number; modelled: number }[]; unmatched: string[] }`; `calibrate(model: CityModel, counts: { station: string; dailyBoardings: number }[]): Calibration`; `UNCALIBRATED: Calibration` (factors 1, stations 0). Factor = median of observed/modelled per mode over matched stations, only when at least 3 matched; IQR reported as `(q3 - q1) / median`.

- [ ] **Step 1: Write tests**: 4 metro stations with observed = 0.5 × modelled → factor 0.5, iqr 0; 2 stations → factor 1 and `stations.metro === 2`; unmatched name listed; `scoreSite` formula contains "calibrated on 4 stations".
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(siting): calibrate boardings against observed station counts`.

### Task 10: Data drawer and desk wiring

**Files:**
- Create: `frontend/src/components/desk/DataDrawer.tsx`, `frontend/src/components/desk/DataDrawer.test.tsx`
- Modify: `frontend/src/components/desk/DeskApp.tsx` (state `data: CityData | null` loaded in an effect from `loadCityData(cityId)`; `model = getCityModel(city, data)`; "Your data" header button; banner swaps to `describeCityData(data)` when data is set; `HexMap hubs={model.hubs}`; `scoreSite(..., model.calibration)`), `frontend/src/components/brief/Briefing.tsx` (same `data` load; data note sentence uses `describeCityData`)

**Interfaces:**
- Consumes: all parsers, `saveCityData`, `clearCityData`, `describeCityData`, `calibrate`.
- Produces: `<DataDrawer open cityId city data onChange(data) onClose />`.
  Three sections (Boundary, Stations, Counts), each with a file input (`accept` `.geojson,.json` / `.zip,.csv` / `.csv`), the parser report list, the current source, a Remove button. "Clear all" and "Export data (JSON)" at the foot. Stations section chooses `parseGtfsZip` for `.zip` and `parseStationsCsv` otherwise. Counts section shows the observed-versus-modelled table from `model.calibration.matched` with per-station error `(observed − modelled) / modelled` and the unmatched names.

- [ ] **Step 1: Write component tests**: dropping a stations CSV (`File` with text) calls `onChange` with `hubs.stations.length === 2` and shows the report; parser error shows the message and does not call `onChange`; Remove clears the section; Clear all calls `onChange(null)`.
- [ ] **Step 2–4: fail, implement, pass.** Also extend `DeskApp.test.tsx`: with a stored `CityData` (seed `localStorage` in the test) the banner shows "Stations: 2 from stations.csv".
- [ ] **Step 5: Run the full frontend suite, type-check and lint.** Commit `feat(desk): Your data drawer: boundary, stations, counts, calibration table`.

## Phase C: scenarios

### Task 11: Scenario model, evaluation and URL encoding

**Files:**
- Create: `frontend/src/lib/pulse/scenario.ts`
- Test: `frontend/src/lib/pulse/scenario.test.ts`

**Interfaces:**
- Produces:
  - `type Alignment = "elevated" | "underground" | "at-grade"`
  - `interface Scenario { id: string; cityId: string; name: string; mode: ModeId; alignment: Alignment; stations: { lat: number; lng: number; name?: string }[]; costs?: CostTable; notes?: string; createdAt: string; updatedAt: string }`
  - `interface CostTable { perKmCr: Record<Alignment, number>; perStationCr: Record<Alignment, number> }`; `DEFAULT_COSTS = { perKmCr: { elevated: 250, underground: 600, "at-grade": 120 }, perStationCr: { elevated: 60, underground: 250, "at-grade": 20 } }`; `COST_SOURCE` string ("order-of-magnitude figures from published Indian metro DPRs and MoHUA appraisals, 2024; edit to match your DPR").
  - `SPACING_KM: Record<ModeId, [number, number]> = { metro: [0.8, 2.0], brt: [0.4, 1.2], feeder: [0.4, 1.2] }`
  - `interface NetworkResult { stations: (SiteResult & { name: string; spacingKmToNext?: number; spacingWarning?: string })[]; boardings: number; newBoardings: number; newShare: number; residents: number; jobs: number; coverageNow: number; coverageAfter: number; lengthKm: number; spacingCompliance: number; costCr: number; costPerBoardingLakh: number; score: number; formula: string; costFormula: string }`
  - `evaluateScenario(model: CityModel, scenario: Scenario): NetworkResult` (stations scored in order against `existingCoverage` plus earlier stations' feeder bands, as `suggestSites` does; residents and jobs over the union of walk cells weighted by max share; `lengthKm` = sum of consecutive `hexDistanceKm`; `score = Math.round(50 × min(1, boardings / (n × reference)) + 30 × newShare + 20 × spacingCompliance)`; `costCr = lengthKm × perKm + n × perStation`; `costPerBoardingLakh = costCr × 100 / boardings`)
  - `newScenarioId(): string` (8 chars from `abcdefghjkmnpqrstuvwxyz23456789`)
  - `encodeScenario(s: Scenario): string` → `m.e.12.9716,77.5946;12.9800,77.6000` (mode initial `m|b|f`, alignment initial `e|u|g`, 4-decimal lat,lng pairs)
  - `decodeScenario(text: string, cityId: string): Scenario | null` (null on any malformed part, fewer than 1 station, or a coordinate more than 100 km from the city centre; `name` = "Shared line")
  - `scenarioFromSuggestions(model, modeId, suggestions: Suggestion[]): Scenario`

- [ ] **Step 1: Write tests**: two-station metro line in Chennai → `lengthKm` equals the hex distance, cost = length × 250 + 2 × 60, `spacingCompliance` 1 when 1.2 km apart and 0 when 0.3 km apart with a warning string "0.3 km to the next station, below the 0.8 km band"; second station's `newBoardings` is lower than when scored alone (cannibalisation); encode → decode round trip preserves mode, alignment, coordinates to 4 decimals; `decodeScenario("x", "chennai") === null`; a Mumbai coordinate under `cityId: "chennai"` → null; score formula string contains "50 x min(1,".
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(scenario): line scenarios: network evaluation, cost sketch, URL encoding`.

### Task 12: Scenario library

**Files:**
- Create: `frontend/src/lib/pulse/scenarioStore.ts`
- Test: `frontend/src/lib/pulse/scenarioStore.test.ts`

**Interfaces:**
- Produces: `listScenarios(cityId?: string): Scenario[]` (newest `updatedAt` first); `saveScenario(s: Scenario): void` (upsert by id, sets `updatedAt`); `removeScenario(id: string): void`; `getScenario(id: string): Scenario | null`; `exportScenarios(cityId?: string): string` (JSON `{ version: 1, scenarios }`); `importScenarios(json: string): { added: number; error?: string }` (validates version, shape, `stations.length ≥ 1`, regenerates ids that collide); storage key `metropulse.scenarios.v1`, same throwing-storage fallback as Task 7.

- [ ] **Step 1: Write tests**: save/list/get/remove; ordering; export/import round trip; import of `{ version: 2 }` → error; throwing storage still lists what was saved this session.
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(scenario): local scenario library with JSON import and export`.

### Task 13: Line mode in the desk

**Files:**
- Modify: `frontend/src/components/desk/HexMap.tsx` (new props `line?: Point[]` drawn as an indigo polyline with dashed casing; `walk` and `feeder` already accept sets, the desk passes the union; markers of kind `"station"` render as numbered indigo circles), `frontend/src/components/desk/SitingPanel.tsx` (new props: `line: Scenario | null`, `network: NetworkResult | null`, `onLineMode(on: boolean)`, `onRemoveStation(k)`, `onMoveStation(k, dir)`, `onAlignment`, `onCosts`, `onSave`, `onRename`, `onCopyLink`, `scenarios: Scenario[]`, `onOpenScenario(id)`, `onDeleteScenario(id)`; a "Stop / Line" toggle at the top; in Line mode the panel shows the network stats, the per-station list with spacing warnings, the cost table with editable per-km and per-station inputs and `COST_SOURCE`, the formula lines, Save / Copy link / Compare buttons, and the saved scenarios list), `frontend/src/components/desk/DeskApp.tsx` (state `line: Scenario | null`; in Line mode a map click appends a station; "Suggest 3 sites" in line mode becomes "Suggest a line" calling `scenarioFromSuggestions`; URL: `?s=<encoded>` when a line exists, `?scenario=<id>` when it was opened from the library; `deskHref` gains `line?: string`), `frontend/src/app/desk/page.tsx` (parse `s` and `scenario`; pass `initialScenario`)
- Test: `frontend/src/components/desk/DeskApp.test.tsx`, `frontend/src/components/desk/SitingPanel.test.tsx` (new)

**Interfaces:**
- Consumes: Task 11 and 12 exports.
- Produces: `DeskAppProps.initialScenario?: Scenario`; `deskHref(cityId, tab, incident?, suggest?, line?: string)`.

- [ ] **Step 1: Write tests**: rendering with `initialScenario` of 2 stations shows "2 stations" and a score; clicking the map twice in Line mode adds two stations (use the existing `HexMap` test approach for `onPick`); a bad `?s=` (desk page passes `initialScenario: undefined` after `decodeScenario` returned null) renders the desk and the notice "That shared line could not be read"; Save adds to `listScenarios`; Copy link puts `s=` in the clipboard stub.
- [ ] **Step 2–4: fail, implement, pass.** Keep `DeskApp.tsx` under 600 lines by moving the line-mode handlers into `frontend/src/components/desk/useLineScenario.ts` (hook returning `{ line, network, addStation, removeStation, moveStation, setAlignment, setCosts, save, rename, open, clear }`).
- [ ] **Step 5: Full suite, type-check, lint. Commit** `feat(desk): line mode: build, score, save and share a line of stations`.

### Task 14: Compare page and alternatives table

**Files:**
- Create: `frontend/src/app/compare/page.tsx`, `frontend/src/components/compare/Compare.tsx`, `frontend/src/lib/pulse/alternatives.ts`
- Test: `frontend/src/lib/pulse/alternatives.test.ts`, `frontend/src/components/compare/Compare.test.tsx`

**Interfaces:**
- Produces: `alternativesCsv(rows: { label: string; r: NetworkResult; s: Scenario }[]): string` and `alternativesMarkdown(rows): string` with columns Option, Mode, Stations, Length (km), Daily boardings, New share, Walk-band coverage after, Capital cost (₹ cr), Cost per daily boarding (₹ lakh), Score; `/compare?city=<id>&a=<enc|id>&b=<enc|id>` resolves each of `a`, `b` through `getScenario` then `decodeScenario`; a missing side shows "Pick a saved scenario" with the library list.

- [ ] **Step 1: Write tests**: CSV has 10 columns and 3 lines for two options; Markdown table has a header separator; Compare renders two names, a delta column where boardings delta is signed, and the two download buttons.
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(compare): side-by-side scenarios with a DPR alternatives table`.

### Task 15: Proposed line in the briefing

**Files:**
- Modify: `frontend/src/components/brief/Briefing.tsx` (prop `scenario?: Scenario`; when present, the "recommended sites" section becomes "Proposed line: <name>" with the per-station table (name, boardings, new share, spacing), the totals, the cost sketch with `COST_SOURCE`, and the headline becomes "<City>: <n> incidents this week, and <name> would carry <boardings> boardings a day"), `frontend/src/app/brief/page.tsx` (parse `s` and `scenario`)
- Test: `frontend/src/components/brief/Briefing.test.tsx` (new)

- [ ] **Step 1: Write tests**: without a scenario the headline contains "the next station belongs"; with a 2-station scenario it contains "would carry" and a table with 2 rows.
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(brief): briefing carries a proposed line`.

## Phase D: public face and API

### Task 16: City summary and the JSON API

**Files:**
- Create: `frontend/src/lib/pulse/summary.ts`, `frontend/src/lib/api/envelope.ts`, `frontend/src/app/api/v1/cities/route.ts`, `frontend/src/app/api/v1/cities/[id]/route.ts`, `frontend/src/app/api/v1/cities/[id]/incidents/route.ts`, `frontend/src/app/api/v1/cities/[id]/site-score/route.ts`, `frontend/src/app/api/v1/cities/[id]/suggest/route.ts`, `frontend/src/app/api/v1/cities/[id]/scenario/route.ts`, `frontend/src/app/api/v1/[...rest]/route.ts` (404 envelope)
- Test: `frontend/src/lib/pulse/summary.test.ts`, `frontend/src/app/api/v1/api.test.ts` (calls the route handlers directly with `new Request(...)`)

**Interfaces:**
- Produces: `citySummary(model: CityModel): CitySummary` where `CitySummary = { id, name, state, population, dailyTrips, peakHour, coverageNow, coverageAfter, incidents: { total, surges, drops }, topIncidents: Incident[3], suggested: { name, boardings, newShare, score, lat, lng }[3], headline: string, lede: string }` (move the headline/lede composition out of `Briefing.tsx` into this function and reuse it there); `ok(data, meta?)` / `fail(status, code, message)` → `Response` with `Cache-Control: public, max-age=3600` and `Access-Control-Allow-Origin: *`; `site-score` validates `lat`, `lng` numeric and within 100 km, `mode` in `MODES`; `suggest` clamps `k` to 1–5; `scenario` POST validates the body with `decodeScenario`-equivalent checks and returns `NetworkResult` without `walkCells`/`feederCells`.

- [ ] **Step 1: Write tests**: `GET /api/v1/cities` → 30 items, `success: true`; unknown city → 404 envelope `{ code: "city_not_found" }`; `site-score` without `lat` → 400 `{ code: "bad_request" }`; `suggest?k=9` → 5 items; `scenario` POST with 2 stations → `boardings > 0`; catch-all → 404.
- [ ] **Step 2–4: fail, implement, pass.** Route handlers export `dynamic = "force-static"` where there are no query parameters (`cities`, `[id]`, `incidents`) and `revalidate = 3600`.
- [ ] **Step 5: Commit** `feat(api): public JSON API v1 for cities, incidents, siting, suggestions and scenarios`.

### Task 17: City pages, OG image, sitemap, robots

**Files:**
- Create: `frontend/src/app/city/[id]/page.tsx` (`generateStaticParams`, `dynamicParams = false`, `generateMetadata`), `frontend/src/app/city/[id]/opengraph-image.tsx` (`ImageResponse`, 1200×630, paper ground, city name in a serif fallback, the headline, the wordmark text), `frontend/src/app/sitemap.ts` (home, desk, developers, privacy, 30 city pages), `frontend/src/app/robots.ts`
- Test: `frontend/src/app/city/city-page.test.tsx` (render the page component for `chennai`: headline, four figures, three incidents, three sites, links to `/desk?city=chennai`, `/brief?city=chennai`, `/compare?city=chennai`)

- [ ] **Step 1: Write the test.** **Step 2–4: fail, implement, pass.** `next build` must list 30 `/city/[id]` pages as static (check the build output in Task 19).
- [ ] **Step 5: Commit** `feat(web): static city pages with Open Graph cards, sitemap and robots`.

### Task 18: Developers and privacy pages

**Files:**
- Create: `frontend/src/app/developers/page.tsx` (endpoint table, envelope, one curl example per endpoint, the data caveat, "no rate limit at this layer; the host's limits apply"), `frontend/src/app/privacy/page.tsx` (no accounts, no analytics, files parsed in the browser and kept in `localStorage` on that device, nothing uploaded; the backend's agent socket is the one exception and is off by default)
- Modify: `frontend/src/app/page.tsx` footer links (Developers, Privacy)

- [ ] **Step 1: Render tests** for both pages (headings present; developers page lists six endpoints).
- [ ] **Step 2–4: fail, implement, pass.**
- [ ] **Step 5: Commit** `feat(web): developers and privacy pages`.

## Phase E: quality and release

### Task 19: Playwright smoke suite in CI

**Files:**
- Create: `frontend/playwright.config.ts` (chromium only, `webServer: npm run start` on port 3100 after `npm run build`, `baseURL`), `frontend/e2e/smoke.spec.ts`
- Modify: `frontend/package.json` (`@playwright/test` dev dependency, scripts `e2e`, `e2e:install`), `.github/workflows/ci.yml` (job `e2e-frontend`: `npm ci`, `npx playwright install --with-deps chromium`, `npm run build`, `npm run e2e`; `deploy` needs it), `frontend/.gitignore` (`playwright-report`, `test-results`)

- [ ] **Step 1: Write the spec**: landing loads and "Open the desk" navigates to `/desk?city=chennai`; the three tabs switch; Line mode: two map clicks produce "2 stations"; Copy link is present; `/compare?city=chennai&a=m.e.13.0827,80.2707;13.0500,80.2500` renders the delta column; `/brief?city=pune` shows "Pune:"; `/city/mumbai` shows the headline; `GET /api/v1/cities` returns 30; `/developers` and `/privacy` render.
- [ ] **Step 2: `npm i -D @playwright/test` and `npx playwright install chromium`; run `npm run build && npm run e2e`** → all pass locally (build under a 2 GB cap if the machine needs it: `NODE_OPTIONS=--max-old-space-size=2048`).
- [ ] **Step 3: Add the CI job. Commit** `test(e2e): Playwright smoke suite for the desk, compare, brief, city pages and API; CI job`.

### Task 20: Landing, docs, changelog and version

**Files:**
- Modify: `frontend/src/app/page.tsx` (hero sub-line adds "Bring your own data. Draw a line, not a stop. Compare alternatives."; a new section "Your city, your data" with the three file types and the privacy line; the loop section's Siting card mentions lines; pricing wording: Explorer "everything in the browser, your data never uploaded", Desk "hosted workspaces, team sharing, unbranded briefings, support", Authority unchanged; footer links), `README.md` (2.0 feature sections: Your data, Lines, Compare, City pages, API; "Try it" unchanged; How it works tree adds `import/`, `scenario.ts`, `calibrate.ts`, `summary.ts`; Known gaps rewritten; test counts), `docs/PRODUCT.md` (roadmap "Now" moves Next's connectors, scenarios and compare into shipped; "Next" becomes workspaces, GTFS-RT, calibration with OD data), `docs/ARCHITECTURE.md`, `SETUP.md`, `docs/LIMITATIONS.md` (calibration scales, does not rebuild the field; cost sketch is an assumption table), `docs/DEMO.md` (add the line and compare beats), `AGENTS.md` (new folders, commands incl. `npm run e2e`), `CHANGELOG.md` (`## [2.0.0] - 2026-11-03`), `frontend/package.json` version `2.0.0`
- Create: `docs/screenshots/` new captures for the drawer, line mode and compare (Playwright screenshot script `frontend/e2e/screenshots.ts`, run manually)

- [ ] **Step 1: Make the landing edits and run its render test and lint.**
- [ ] **Step 2: Update every document listed; grep for "3 sites", "sample city model" and "illustrative" to make sure each mention now says "until your data is loaded in the Your data drawer".**
- [ ] **Step 3: Capture screenshots with the script; reference them from the README.**
- [ ] **Step 4: Run both suites, type-check, lint, `next build`, and `npm run e2e`.** Record the counts in README.
- [ ] **Step 5: Commit** `docs: MetroPulse 2.0 release notes, landing and documentation` and tag `v2.0.0` locally (do not push).

## Self-review notes

- Spec §1 (your data) → Tasks 3–10; §2 (scenarios) → 11–15; §3 (public face, API) → 16–18; §4 (repository) → 1, 2, 19, 20.
- Review Focus 1 → Task 4; 2 → Tasks 3, 5; 3 → Tasks 6, 9; 4 → Tasks 7, 12; 5 → Tasks 11, 13.
- Names used across tasks: `CityData`, `Station`, `ParseResult`, `getCityModel(city, data?)`, `CityModel.hubs/data/calibration`, `Calibration`, `Scenario`, `NetworkResult`, `evaluateScenario`, `encodeScenario`/`decodeScenario`, `listScenarios`/`saveScenario`/`getScenario`, `citySummary`, `deskHref(..., line?)`.

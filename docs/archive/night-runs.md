# Night run 2026-10-20

Branch: `night-run/2026-10-20` (from `feat/india-twin`). Nothing pushed.

## What changed
1. `chore`: gitignored `.impeccable/`.
2. `fix(deps)`: `psycopg2-binary` added to `requirements.txt` and `pyproject.toml`. `twin/store/pg_sync.py` imports it, but it was never declared.
3. `chore(nl_engine)`: removed the stale TODO on `ConversationManager.advance()`. It pointed at the deleted `app/ws/simulation.py`. The method now has a proper docstring and 2 state-machine tests.
4. `feat(ws)`: **`/ws/agent` re-mounted** with the guards the M2 plan asked for:
   - It is disabled unless `AGENT_WS_TOKEN` is set. The token is accepted as `?token=` or `Authorization: Bearer`, compared with `hmac.compare_digest`. A bad or missing token closes with 1008 before accept, which a browser sees as HTTP 403.
   - `WS_MAX_CONNECTIONS` is enforced. A connection over the limit closes with 1013, and the slot is always released in `finally`.
   - Exception text no longer reaches the client. Messages are capped at 4000 chars, non-object JSON is rejected, and `WebSocketDisconnect` is handled.
   - Documented in `backend/.env.example` and AGENTS.md. `test_twin_api.py`'s "no websockets in M1" test now asserts that `/ws/agent` is the only socket.
5. `feat(ui)` / `fix(ui)`: changes to the twin dashboard:
   - A "Loading district boundaries..." indicator.
   - A first-visit hint.
   - A dismissible error banner, placed bottom-centre so it no longer overlaps the search box.
   - A skeleton loader in the place panel.
   - Panel errors now come with a "Try again" button.
   - PlaceCard has an empty state.
   - New store actions: `retry()` and `dismissError()`.
   - Bug fixed: dismissing a boundary error used to leave the map on "Loading" forever.

## How to run and test
```
cd backend
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m spacy download en_core_web_sm
.venv\Scripts\python -m pytest tests/unit tests/integration -q
cd ..\frontend && npm test && npm run type-check && npm run lint
```
To try the agent socket: set `AGENT_WS_TOKEN=...` in `backend/.env` and connect to `ws://localhost:8000/ws/agent?token=...`. Send `{"type":"AGENT_START","message":"..."}`. A real LLM key is needed for useful answers. Without one, the client gets a generic AGENT_ERROR.

## Verified
- Backend: 738/738 pass. Before this run, 11 test modules failed to collect because the local venv was missing pandas, geopandas, rasterio, psycopg2 and spaCy. Those are now installed in `.venv`.
- Frontend: 18/18 jest tests pass. Type-check and lint are clean.
- Live check: ran uvicorn and `next dev`, probed `/ws/agent` (403 on a bad or missing token, PONG with a good one), and took Playwright screenshots of the error, dismissed and hint states at phone width.

## Left / ideas
- Per-user Supabase Auth on `/ws/agent` (spec §4). The shared token is only a stopgap.
- A frontend agent chat client. None exists yet.
- Twin data is not built locally (`data/twin` has only `manual/` and `seed/`). Run `python scripts/twin_build.py build` to see the real map.
- `next.config.js` still defaults `NEXT_PUBLIC_WS_URL` to the retired `/ws/simulate`.
- The `docs/LIMITATIONS.md` modelling items (1-8, 11) need real data sources, so they don't fit a night run.

---

# Night run 2026-10-24 (branch `night-run/2026-10-24`, from `night-run/2026-10-20`)

## What changed
1. `fix(config)`: `next.config.js` now defaults `NEXT_PUBLIC_WS_URL` to `ws://localhost:8000/ws/agent` (was the retired `/ws/simulate`).
   `frontend/.env.local.example`, README and SETUP still mention `/ws/simulate`. They were left alone because the run brief said not to touch `.env*` files.
   The client also rewrites a `/ws/simulate` URL to `/ws/agent`, or derives the URL from `NEXT_PUBLIC_API_URL`, so stale envs still work.
2. `feat(api)`: new `GET /api/agent/status` returning `{enabled, available, path}`. It never returns the token. A browser only sees close code 1006 for a socket rejected before accept, so the UI uses this to tell "disabled" apart from "bad token" and "backend down". 2 new backend tests.
3. `feat(ui)`: an agent chat panel (`src/components/agent/AgentChat.tsx`, logic in `src/lib/agentChat.ts`), opened with the "Ask the agent" button at the bottom right of the map.
   - Status pill: Checking, Disabled, Backend offline (with retry), Ready, Connecting, Connected.
   - The access token is typed in and stored in sessionStorage only. It is never `NEXT_PUBLIC_*`.
   - Streams AGENT_THINK, AGENT_ACTION and AGENT_RESULT as they arrive. AGENT_ASK renders option buttons and the reply is sent as AGENT_REPLY.
   - Shows AGENT_ERROR text. A refused or dropped socket gets its own message (1013 busy / 1008 refused / 1006 unreachable).
   - Stop and Clear buttons. Messages shorter than 4 characters are rejected client-side.
   - The status check runs only when the panel is opened, so existing page tests are unaffected.
   - 18 new jest tests: reducer, parser and URL logic, plus component tests with a mock WebSocket.

## Verified
- Backend 740/740 (738 + 2). Frontend jest 36/36. Type-check and lint are clean.
- Live check, uvicorn :8010 with `AGENT_WS_TOKEN` passed via the process environment (no .env edits), plus `next dev` :3010, screenshotted with headless playwright-core at desktop and phone widths:
  - Good token: AGENT_START then AGENT_ERROR "internal error". No LLM key is set locally, so this is expected.
  - Wrong token: 403, and the UI shows "Could not reach the agent...".
  - Backend started with an empty token: the panel shows "Disabled".

## Left
- Per-user auth on `/ws/agent` (spec §4). The shared token is still a stopgap.
- Update `.env.local.example`, README and SETUP away from `/ws/simulate`. This was out of scope tonight.
- Twin data build (`scripts/twin_build.py build`). Without it the map shows "twin data not built".
- No real-LLM end-to-end run of the chat. It needs an API key.

## Follow-up (late wave, docs only)
- README: WebSocket Protocol section rewritten for `/ws/agent` (AGENT_WS_TOKEN, `?token=`/Bearer, 1008/1013 closes, AGENT_* message types, PING/PONG); endpoint table adds `/api/agent/status`; architecture box no longer lists `/ws/simulate`.
- SETUP: `.env.local` sample uses `/ws/agent`, explains the token lives only in `backend\.env` (never `NEXT_PUBLIC_*`), 3 new troubleshooting rows.
- `frontend/.env.local.example` (example file, no secrets): `/ws/agent` plus token comments.
- Not touched: historical plans/specs under `docs/` and IMPLEMENTATION_PLAN.md still mention `/ws/simulate` (historical records).

## Late wave: twin data build and screenshots (02:24-02:35)
- Did not build: `backend/scripts/twin_build.py build` won't start until all 7 manual files are in `data/twin/manual/`. LGD (captcha), Survey of India (login) and VIIRS (free account) need a browser session, so nothing was downloaded. The exact steps are in `_night_run/2026-10-24/NEEDS_INPUT.md`. No data screenshots were taken and the README is unchanged.
- `feat(ui)`: a "not built" 503 now shows a setup panel (`components/twin/TwinNotBuilt.tsx`) in place of the red banner. It has 4 steps (check, manual downloads, build with `--boundary-version`, reload) and Reload/Hide buttons. On phones the panel is compact and stays clear of the "Ask the agent" button.
- The backend 503 message now names `data/twin/manual/README.md` and the required `--boundary-version lgd-YYYYMMDD` flag. Before, it said `run scripts/twin_build.py build`, which fails without that flag.
- Verified: twin API tests 15/15, jest 37/37, tsc and lint clean. Live run on uvicorn :8012 (with `CORS_ORIGINS=http://localhost:3012` passed via the shell) and next dev :3012. Headless Chrome screenshots at 1440 and 390 px had no horizontal scroll. They are kept in scratch only, not committed. Both servers were stopped.
- Gotcha: when the frontend runs on a port other than 3000, the backend needs `CORS_ORIGINS` set or every fetch fails with "Failed to fetch".

## Late wave: API benchmark (05:51-06:05, after a usage-limit pause)
- New `scripts/bench_api.py`: benchmarks an already-running backend (starts nothing). Warm-up, then N requests at concurrency 1 and 8 for 7 REST endpoints that need no twin data / LLM key, plus the `/ws/agent` handshake and PING/PONG when `AGENT_WS_TOKEN` is set. Writes `docs/benchmarks.md` with machine info and a load caveat. Options: `--requests`, `--ws-requests`, `--warmup`, `--concurrency`, `--endpoints`, `--server-note`, `--out`.
- New `backend/tests/unit/test_bench_stats.py` (10 tests): percentile vs hand values and `numpy.percentile`, `summarize`, error cases.
- Ran it for real: uvicorn :8020 (1 worker, `SUPABASE_URL`/`SUPABASE_KEY` blanked and `AGENT_WS_TOKEN` set via the shell, no .env edits). c=1 p50 0.8-2.6 ms, p99 <= 4.1 ms, 380-1189 req/s; c=8 p99 13-100 ms. All 2xx. Machine was at 67-78% CPU / 86% RAM from other agents, noted in the report. Server stopped by its PID.
- Backend 750/750.
- Gotcha: on this machine a uvicorn started via PowerShell `Start-Process` or bash `exec .venv/Scripts/uvicorn.exe` exited immediately; `python -m uvicorn` in a background bash worked.
- Not measured: twin endpoints with real data (not built), agent runs (need an LLM key), the legacy engine.

---

# Night run 2026-10-31 (branch `night-run/2026-10-31`, from `night-run/2026-10-24`)

## What changed
1. `test(agent-chat)`: `/ws/agent` client now retries a 1013 (busy) refusal before the session starts with 1s/2s/4s backoff (max 3; `backoffDelay`/`shouldRetry` in `lib/agentChat.ts`); Stop/unmount cancel it; 1006/1008 and mid-session drops are not retried. Shared `src/test-utils/mockWebSocket.ts`; new `AgentChat.socket.test.tsx` (connect URL/encoding, frame order, malformed/unknown frames, backoff timing with fake timers, error states, invalid URL, Clear). Jest 37 -> 54. CI runs `npm run test:ci` (`jest --ci --runInBand`).
2. `fix(ui)`: "Ask the agent" overlapped the place panel's footer on desktop; it now sits left of the panel (`besidePanel` prop, sm+ only).
3. `docs`: README rewritten to describe what exists (India Twin + agent) with real numbers (16 REST endpoints, 6 indicators, 5 agent tools, 30 city configs, 20 case studies, 750 BE / 54 FE tests, benchmark link). Removed the retired 3-loop simulator, fake metric panels, fake coverage bars, "COMPLETE" deployment roadmap, nonexistent file tree, MIT claim (there is no LICENSE file). AGENTS.md counts updated.
4. `docs/screenshots/` (4 PNGs, 50-155 KB): agent THINK and ASK steps from real runs against local Ollama gemma4; place panel from the **test-fixture** twin (synthetic squares; captioned as such); fresh-clone "not built" panel. No cascade view exists any more.

## How the screenshots were made
uvicorn :18110 (`SUPABASE_*` blanked, `AGENT_WS_TOKEN`, `LLM_PROVIDER=ollama`, `LLM_TIMEOUT_MS`, `CORS_ORIGINS`, `TWIN_DATA_DIR` all via the shell, no .env edits) + `next dev` :18111; fixture twin built with `make_fixture_manual_paths` + `twin_build build --boundary-version lgd-fixture` into scratch; playwright-core installed in scratch, system Chrome headless. Servers stopped by recorded PID.

## Verified
BE 750/750; FE jest 54/54, tsc, lint clean, `next build` OK.

## Left
- No agent run reached AGENT_RESULT: Ollama was shared with other agents (model swaps), steps took 25-150 s and two runs hit the LLM timeout. A hero shot of a finished answer needs an idle machine or a hosted key.
- Real twin data build still blocked on manual downloads (LGD/SOI/VIIRS).
- Unused simulator-era deps in frontend/package.json (@tremor/react, h3-js, katex, react-markdown) could be pruned.
- docs/ARCHITECTURE.md still describes the simulator in places.
- No LICENSE file (README previously claimed MIT) - see NEEDS_INPUT.

---

# Night run 2026-11-02 (branch `night-run/2026-11-01`, from `night-run/2026-10-31`)

## What changed
1. `chore(deps)` frontend: removed `@tremor/react`, `katex`, `react-markdown`, `remark-gfm`, `h3-js`, `date-fns`, `@deck.gl/extensions`, `@deck.gl/mapbox`, `ts-jest` (141 packages out of node_modules). Proof: no import/require/dynamic import anywhere in `src/` or configs; jest uses `next/jest` (SWC), not ts-jest. Dropped the tremor glob from `tailwind.config.ts`. Kept `deck.gl`: `IndiaMap` imports `@deck.gl/react` and `@deck.gl/core`, which only arrive through it (replacing it with explicit `@deck.gl/core`+`react`+`widgets` is a possible follow-up).
2. `chore(deps)` backend: removed `scipy`, `python-multipart`, `pytest-benchmark` from requirements.txt and pyproject. Proof: zero imports; no `Form`/`File`/`UploadFile` in source (python-multipart was not even installed in .venv); no `benchmark` fixture. Uninstalled scipy + pytest-benchmark from `.venv` and reran everything. Kept `uvicorn` (Dockerfile CMD), `python-dotenv` (pydantic-settings env_file), `websockets` (uvicorn WS + bench script), `pyarrow` (pandas parquet engine), `locust` (tests/load).
3. `docs/ARCHITECTURE.md` rewritten from the code: components, live vs dormant modules (found by importing `app.main` and listing `sys.modules`), twin read/build flow, agent pipeline (sequence diagram), storage, external services, config, known limits, mermaid diagrams.
4. README: endpoint params/payloads corrected (resolve takes `state`, boundaries serve country/state/district as plain GeoJSON, place detail fields), null-value claim corrected, known gaps refreshed, test counts. SETUP.md rewritten (it still described the simulator, a Mapbox token and sliders).
5. Bugs fixed (each with a failing test first):
   - `GET /api/regions/{bad-name}/profile|baseline` returned 500 (CityConfig's ValueError) -> now 404.
   - `call_llm(provider=X)` sent the configured provider's model to X -> per-provider default unless X is the configured provider.
   - Realtime snapshot quality counted connector attempts, so a GDELT fallback after a Google News failure lowered quality (5/6) -> now counted per domain.
   - Agent prompts no longer claim "powered by Gemma".
6. Tests: backend 750 -> 801 (`test_agent_loop.py` 21, `test_llm_call.py` 8, `test_api_routes.py` 17, `test_ingestion_cycle.py` 5). Frontend 54 -> 68 (`twinApi.test.ts`, `TwinNotBuilt.test.tsx`).

## Verified
BE 801/801 (memcap 2 GB, peak 0.45 GB); import smoke of all 69 app/engine/twin modules OK with scipy removed; `twin_build.py --help`, `bench_api.py --help` OK. FE jest 68/68, tsc and lint clean, `next build` OK (peak 1.27 GB under a 2 GB cap, heavy lock held).

## Left
- `POST /api/ingest` is unauthenticated (anyone can trigger outbound fetches) - needs a decision (admin token?).
- Existing `test_ingestion_cycle_*` in `test_realtime.py` still hit the real network with soft asserts.
- Dormant simulator-era modules (`app/rag`, `engine/translator.py`, ...) could be deleted with their tests; not done (product decision).
- Earlier items still open: per-user agent auth, real twin build (manual downloads), no LICENSE.

## Second wave (02:20-, same branch)

### What changed
1. **Hermetic backend suite.** New `backend/tests/conftest.py`:
   - Sets `SUPABASE_URL/KEY`, LLM keys, `LLM_PROVIDER/MODEL`, `EMBEDDING_*`, `INGEST_TOKEN` to empty/defaults and `OLLAMA_BASE_URL=http://127.0.0.1:9` before any app import (env beats `.env`). **Finding:** before this, the suite used the developer's `backend/.env`, so `DatabaseClient` tests (e.g. the ingestion-cycle tests' `save_city_snapshot`, `/api/data-sources`) read and upserted the live Supabase project.
   - Autouse guard: `socket.getaddrinfo`, `socket.socket.connect/connect_ex` and asyncio `sock_connect` (selector + Windows proactor loops, which skip `socket.connect` for IP literals) allow loopback/unix only. Blocked attempts raise `NetworkBlocked(OSError)` and are recorded; the test fails at teardown even if the code swallowed the error (the connectors catch everything). Opt-out marker `@pytest.mark.allow_network`.
   - First run with the guard caught exactly: the 3 `test_ingestion_cycle_*` + 2 `*_fetch_handles_network_error` tests (real Google News/GDELT) and the Supabase call above. Nothing else.
2. `test_realtime.py`: connectors and ingestion cycles run on `httpx.MockTransport` serving hand-written fixtures (`tests/fixtures/realtime/google_news_rss.xml`, `gdelt_artlist.json`; shape-faithful, synthetic titles, not recorded from the live feeds). Soft asserts replaced with exact ones (fresh 5/5; Google News down -> GDELT fallback 2/5 degraded; unknown city + feeds down -> None; retry count 3). Suite time 66 s -> 16 s (no real retries/back-off).
3. `test_network_guard.py` (19): host classification, loopback still works (sync + asyncio), and subprocess runs proving a swallowed lookup and an asyncio IP-literal connect fail the inner test, and the opt-out marker works.
4. **Opt-in `INGEST_TOKEN`** for `POST /api/ingest` (`require_ingest_token` in `app/routes/realtime.py`): empty (default) = open as before; set = needs `Authorization: Bearer <t>` or `X-Ingest-Token: <t>` (hmac.compare_digest), else 401 + `WWW-Authenticate: Bearer`, and no fetch happens. Added `X-Ingest-Token` to the CORS allow-list. Documented in README (endpoint table + known gaps), SETUP, ARCHITECTURE, AGENTS.md, `.env.example`. 13 tests in `test_api_routes.py`. Policy (turn it on in deploys? default-on?) left to the user - NEEDS_INPUT updated.
5. `test_agent_tools.py` (21): the live `AgentTools` (parse_scenario / case studies / city profile / list / compare_sectors) and `AgentMemory`. **Bug fixed:** `city_configs or {}` replaced a caller's empty dict (what `/ws/agent` passes), so the per-session cache was never filled -> `is not None`.
6. `test_app_lifespan.py` (10): startup pass + round-robin rotation of `_ingestion_loop`, failures don't stall rotation, no-city case, lifespan starts/cancels the task and closes the shared HTTP client, seeding failure doesn't block startup, CORS preflight.
7. **Frontend Jest guard** in `jest.setup.js`: `fetch`, `WebSocket`, `XMLHttpRequest.send` replaced by stand-ins that throw and fail the test in `afterEach`; tests' own mocks override them. All 68 pass (no test was reaching out); verified with a throwaway test that swallowed fetch/WebSocket errors -> 2 failures.
8. README: test count 867, hermetic-suite rule in Testing.

### Verified
Backend 867/867 (memcap 2 GB, peak 0.53 GB, 16.8 s). Frontend jest 68/68 with `--maxWorkers=2` (peak 0.84 GB; default workers on 16 cores OOM'd the 2 GB cap - use `--maxWorkers=2` locally under memcap), `next lint` clean.

### Left
- Whether to enable `INGEST_TOKEN` in deployments (user decision).
- (done) `_ingestion_loop` now picks the city before the try, so the except branch no longer re-indexes `cities`.
- `status.md` is a 2026-10-20 snapshot (738 tests); README/NIGHT_RUN_NOTES hold current numbers.

---

# Night run 2026-11-02, daytime wave (branch `night-run/2026-11-02`, from `night-run/2026-11-01`)

Worked in a worktree (`_night_run/2026-11-02/wt/MetroPulse`). The user's checkout was not touched. `backend/.env` was never loaded, and the conftest network guard stayed on.

## What changed
1. Frontend dep prune (task 1): `@tremor/react`, `katex` and `react-markdown` were already removed on `night-run/2026-11-01`. Re-checked: none of them is in package.json, the lockfile or any import in `src/` or the configs. `h3-js` was only a transitive dep of the `deck.gl` umbrella (via `@deck.gl/carto` and `geo-layers`).
   - `chore(deps)`: replaced the `deck.gl` umbrella with what `IndiaMap` imports (`@deck.gl/core`, `react`, `layers`) plus their peers (`@deck.gl/widgets`, `@luma.gl/core`, `@luma.gl/engine`, `@loaders.gl/core`), pinned to the versions already locked. 268 packages are gone, including h3-js, carto, arcgis and google-maps (node_modules went from 653 to 525 top-level entries).
2. Stale simulator text (task 2): ARCHITECTURE.md had already been rewritten, but its "Stale prompt text" note was out of date. The live tool descriptions sent to the LLM on every step still said "simulation platform" and "use this before committing to a full simulation run", and no simulation tool exists.
   - `fix(agent)`: rewrote `AgentTools.get_tool_descriptions()`. `compare_sectors` is now described as what it is: each sector change × that sector's weight, ranked, a static estimate rather than a forecast.
   - Also fixed the exported but unused `AGENT_SYSTEM_PROMPT`.
   - New test `test_prompt_text_does_not_promise_a_simulator`, written first and seen failing.
   - ARCHITECTURE "Known limits" now has a "No forecasting" entry in place of the stale note.
   - README project tree: `simulation/` now marks confidence, overlay and explainability as simulator leftovers.
3. `fix(docker)`:
   - Compose was broken from the start. The frontend used a `Dockerfile` that doesn't exist (now `Dockerfile.dev`). The browser URLs used the compose hostname `backend` and `/ws/simulate` (now `localhost:8000` and `/ws/agent`). The backend couldn't see the repo-level `data/` (now mounted read-only at `/data`, which is where `engine/config.py` and `twin/paths.py` resolve it inside the container).
   - New `backend/.dockerignore`: `COPY . .` used to bake `backend/.env` and `.venv` into the image. That affects Fly deploys, which now need `fly secrets` (see NEEDS_INPUT).
   - New `frontend/.dockerignore`: host node_modules no longer overwrites the container's install.
   - Not run: Docker isn't allowed today. The YAML was parsed and the Dockerfile paths checked with Python.
4. `fix(llm)`: the Ollama call now sends `options.num_ctx` from the new `OLLAMA_NUM_CTX` setting. The default is 8192, because the agent prompt grows over up to 15 steps. 0 keeps the server default. Before this it sent nothing, and the server default here (131k) used 18 GB on 10-31. 2 new tests, and the existing request-shape test was updated (written first, seen failing). Documented in `.env.example`, SETUP and ARCHITECTURE. The conftest pins it too.
5. Test counts updated to 870 in README, AGENTS.md and status.md.

## Verified
- Backend 870/870 (memcap 2 GB, peak 0.44 GB, 14 s, CPU only, network guard on). The prompt fix alone gave 868.
- Frontend after the deck.gl swap, from a clean `npm ci`: tsc clean, `next lint` clean, jest 68/68 with `--maxWorkers=2` (peak 0.94 GB).
- Runtime: `next dev` on :18130 with no backend (peak 1.44 GB, stopped by PID). Headless Chrome mounted the `deckgl-overlay` canvas, and the dev log showed no module-resolution errors. The banner said "Failed to fetch", which is expected without a backend.
- No `next build` (memory rule for today).
- The `npm ls` "extraneous @emnapi/wasi-threads" warning predates this run (it is in the old lockfile too).

## Left
- Fly: set secrets before the next deploy. The Fly image also has no `data/` (build context is `backend/`), so city configs and the twin are missing there. This is a deploy decision.
- A `next build` after the deck.gl swap, on a day with memory to spare.
- Earlier items are still open: per-user agent auth, real twin build (manual downloads), no LICENSE, the `INGEST_TOKEN` policy, and deleting the dormant simulator modules.

---

# Night run 2026-11-02, night finishing pass (same branch `night-run/2026-11-02`)

## What changed
1. Committed the re-shot desk screenshots (taken after `aa747a2`, so the map's right-edge labels fit, e.g. Whitefield on the phone shot). Every image the README references exists.
2. `docs/LIMITATIONS.md` and `docs/DATA_CREDIBILITY.md` rewritten for what ships (desk sample model, twin receipts and trust labels, agent estimates, parked news proxies). Both still described the retired simulator (alpha/beta coefficients, confidence decay per simulated month, panels that no longer exist). `docs/RAG_ENGINE.md` marked parked. The four `data/{flood,sez,slums,transit}/README.md` pointed at preprocess scripts that do not exist; they now say nothing reads them yet.
3. Desk bugs found with a headless sweep (every city × alerts/siting-suggest/brief, plus tab, play, incident, pin, suggest flows and phone width), each with a failing test first:
   - 17 city configs list one place twice (urban anchor + special zone), so the map drew doubled labels and React logged duplicate-key errors. `HexMap` now draws each name once (as a hub if either entry is transport).
   - Phone width: the timeline's day labels made the desk scroll sideways by 32 px on every tab. One-letter labels below `sm`.
   - Hydration warnings in Guwahati, Lucknow and Vadodara: Node and Chrome disagreed on the last bit of `Math.cos`, so anchor coordinates differed between server HTML and client. The east-west scale in `buildHexGrid` is rounded to 1e-9. New `geo.test.ts`.
4. AGENTS.md project line describes the desk; test counts 149.

## Verified
Backend 870/870 (memcap 2 GB, peak 0.82 GB). Frontend jest 149/149 (`--maxWorkers=2`, peak ~1.1 GB), tsc and `next lint` clean, `next build` OK (peak 1.63 GB under 3 GB). After the fixes the sweep logged zero console errors across 30 cities and no horizontal overflow at 390 px. Dev server was stopped by PID.

## Left
- The duplicated anchors are also counted twice by the demand model (double weight for those places in 17 cities). Deduping in `scripts/export_sample_cities.py` changes those cities' numbers and needs the detector tests rechecked; a modelling decision, not done.
- No LICENSE (NEEDS_INPUT). INGEST_TOKEN policy, Fly secrets and `data/` in the Fly image are still open.
- Internal files for publishing: see `_night_run/2026-11-02-night/notes/metropulse.md`.

---

# Run 2026-11-03: MetroPulse 2.0, from demo to desk (branch `startup/2026-11-03`, from `integrate/desk-on-main`)

Brief: "transform this project into a complete startup grade one", full authority. Spec and plan
were written first (`docs/superpowers/specs/2026-11-03-startup-grade-design.md`,
`docs/superpowers/plans/2026-11-03-startup-grade.md`), then executed task by task with a test
written and watched to fail before each piece of code.

## What changed
1. **Your data** drawer on the desk: GeoJSON boundary, GTFS static zip or stations CSV, counts CSV.
   Parsed in the browser (`lib/pulse/import/`), only derived data kept in `localStorage`
   (`userdata.ts`), model built on the user's boundary and hubs (`getCityModel(city, data)`),
   calibration factor per mode from observed counts (`calibrate.ts`) shown in the siting formula.
2. **Line mode** on Siting (`scenario.ts`, `LinePanel.tsx`, `useLineScenario.ts`): ordered stations
   scored net of each other, spacing band, editable cost sketch with its source, network score;
   local library with JSON import/export (`scenarioStore.ts`); share links `?s=m.e.lat,lng;...`.
3. **Compare** page with a DPR alternatives table (CSV, Markdown); **briefing** takes a line.
4. **City pages** (30, static) with on-request OG images, sitemap, robots; **JSON API** `/api/v1/*`
   in the backend's envelope; `/developers`, `/privacy`.
5. **Repository**: dormant simulator modules and their tests deleted from the backend,
   `app/llm.py` replaces `app/simulation/llm.py`, stale specs and the night-run notes archived here,
   Apache-2.0 `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, CODEOWNERS, Dependabot, templates,
   four ADRs, `NEEDS_INPUT.md`, Playwright smoke suite in CI, version 2.0.0, CHANGELOG.

## Verified
Backend 906/906 (hermetic). Frontend Jest 259/259 with one worker, lint and type-check clean,
`next build` OK with a 2 GB heap (30 city pages static), Playwright 6/6 against the build.
Screenshots in `docs/screenshots/` (`desk-line`, `desk-your-data`, `compare`, `city-page`) were
taken from the production build with `frontend/e2e/screenshots.ts`.

## Left
- Workspaces (sign-in, cloud-saved scenarios, team sharing) are the next milestone; local-first only today.
- The demand field between stations is still the sample model; calibration scales, it does not fit.
- "Suggest a line" joins the three greedy picks (spread out by design), so it proposes a hub
  network, not a corridor; a corridor-constrained suggestion is a follow-up.
- Owner decisions in `NEEDS_INPUT.md`: licence, pricing wording, terms, security contact,
  `INGEST_TOKEN` policy, production domain.
- Merged to main on the owner's choice, pushed with tags v2.0.0 and v2.1.0; CI (tests, e2e, deploy job) green on origin/main.

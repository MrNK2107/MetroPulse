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

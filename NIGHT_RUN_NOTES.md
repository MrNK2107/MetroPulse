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

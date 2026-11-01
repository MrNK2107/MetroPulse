# MetroPulse — Agent Context

## Project
AI-Powered Macro-Urban Digital Twin Sandbox. Next.js 14 (frontend) + FastAPI (backend) + Supabase PostgreSQL + pgvector.

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Twin data: `cd backend && python scripts/twin_build.py check|build`
- Backend tests: `cd backend && pytest tests/unit tests/integration` (867 tests; needs `python -m spacy download en_core_web_sm`)
- Frontend: `cd frontend && npm run dev`
- Frontend tests: `cd frontend && npm run test` (68 tests; CI uses `npm run test:ci`)
- Lint/typecheck: `cd frontend && npm run lint && npm run type-check`

## India Twin
The legacy city simulator is retired (pre-change state: git tag `legacy-metropulse`). The product is now the India Twin: a sourced map of Indian places and indicators.
- Spec: `docs/superpowers/specs/2026-10-18-india-twin-design.md`; data source notes in `docs/twin/DATA_SOURCES.md`
- Backend package: `backend/twin/` (engine-style: never imports from `app/`); API in `backend/app/routes/twin.py` (`/api/twin/*`)
- Built data: `data/twin/` (produced by `scripts/twin_build.py`)
- Frontend: `frontend/src/components/twin/`, `store/twinStore.ts`, `lib/twinApi.ts`, `types/twin.ts`
- Parked for M2 (not wired to the UI): `engine/agent/` (served by the token-gated `/ws/agent`; frontend client: `components/agent/AgentChat.tsx`), `app/rag/`, `nl_engine/`, `app/realtime*`; legacy city YAMLs in `data/cities/` still back `/api/regions*`

## Security

### Path Traversal Sanitization
`CityConfig.load()` and `CityConfig.load_geojson()` validate `city_name` with `re.fullmatch(r'[a-zA-Z0-9_]+', city_name)` to prevent directory traversal attacks. Zone file paths in `grid.py` also reject `..` patterns.

### WebSocket Auth and Connection Limit
`/ws/agent` is the only WebSocket endpoint (`app/ws/agent.py`, mounted in `app/main.py`). It is **disabled unless `AGENT_WS_TOKEN` is set**; clients send the token as `?token=` or `Authorization: Bearer`, compared with `hmac.compare_digest`. Bad/missing token closes with 1008 before accept. At most `WS_MAX_CONNECTIONS` (default 10) concurrent sessions; extras close with 1013. Client-facing errors are generic (no exception text). Tests: `tests/integration/test_ws_agent.py`. Supabase-Auth-based per-user auth (spec §4) is still to do; the shared token is the interim gate.

### Ingest Token
`POST /api/ingest` is open by default. If `INGEST_TOKEN` is set it requires `Authorization: Bearer <token>` or `X-Ingest-Token: <token>` (constant-time compare, 401 otherwise); see `require_ingest_token` in `app/routes/realtime.py`. Tests: `tests/integration/test_api_routes.py`.

### Tests Never Touch the Network
`backend/tests/conftest.py` blanks Supabase/LLM settings (env beats `.env`) and patches `socket.getaddrinfo`/`connect` to loopback only; any other attempt fails the test at teardown, even if the code swallowed the error. Mock HTTP with `httpx.MockTransport` (see `tests/unit/test_realtime.py`). Mark a deliberate live test with `@pytest.mark.allow_network`.

## Conventions
- Python: Use NumPy vectorized ops where arrays are involved
- TypeScript: strict mode, camelCase props, PascalCase components
- All API responses use `{ success, data, error, meta }` envelope
- Commit format: `type(scope): description` (e.g. `feat(twin): add place index`)

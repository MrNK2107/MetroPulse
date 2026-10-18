# MetroPulse — Agent Context

## Project
AI-Powered Macro-Urban Digital Twin Sandbox. Next.js 14 (frontend) + FastAPI (backend) + Supabase PostgreSQL + pgvector.

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Twin data: `cd backend && python scripts/twin_build.py check|build`
- Backend tests: `cd backend && pytest tests/unit tests/integration` (706 unit + 21 integration tests)
- Frontend: `cd frontend && npm run dev`
- Frontend tests: `cd frontend && npm run test` (13 tests)
- Lint/typecheck: `cd frontend && npm run lint && npm run type-check`

## India Twin
The legacy city simulator is retired (pre-change state: git tag `legacy-metropulse`). The product is now the India Twin: a sourced map of Indian places and indicators.
- Spec: `docs/superpowers/specs/2026-10-18-india-twin-design.md`; data source notes in `docs/twin/DATA_SOURCES.md`
- Backend package: `backend/twin/` (engine-style: never imports from `app/`); API in `backend/app/routes/twin.py` (`/api/twin/*`)
- Built data: `data/twin/` (produced by `scripts/twin_build.py`)
- Frontend: `frontend/src/components/twin/`, `store/twinStore.ts`, `lib/twinApi.ts`, `types/twin.ts`
- Parked for M2 (not wired to the UI): `engine/agent/`, `app/ws/agent.py` (code kept but not mounted; M2 re-mounts `/ws/agent` with auth and connection limits), `app/rag/`, `nl_engine/`, `app/realtime*`; legacy city YAMLs in `data/cities/` still back `/api/regions*`

## Security

### Path Traversal Sanitization
`CityConfig.load()` and `CityConfig.load_geojson()` validate `city_name` with `re.fullmatch(r'[a-zA-Z0-9_]+', city_name)` to prevent directory traversal attacks. Zone file paths in `grid.py` also reject `..` patterns.

### WebSocket Connection Limit
No WebSocket endpoints are mounted in M1: `app/main.py` does not include the parked `/ws/agent` router. The `WS_MAX_CONNECTIONS` setting (`app/config.py` → `ws_max_connections`, default 10) exists but nothing enforces it; M2 re-mounts `/ws/agent` together with auth and connection limits (spec §4).

## Conventions
- Python: Use NumPy vectorized ops where arrays are involved
- TypeScript: strict mode, camelCase props, PascalCase components
- All API responses use `{ success, data, error, meta }` envelope
- Commit format: `type(scope): description` (e.g. `feat(twin): add place index`)

# MetroPulse — Agent Context

## Project
AI-Powered Macro-Urban Digital Twin Sandbox. Next.js 14 (frontend) + FastAPI (backend) + Supabase PostgreSQL + pgvector.

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Backend tests: `cd backend && pytest tests/unit/` (378+ unit tests)
- Frontend: `cd frontend && npm run dev`
- Frontend tests: `cd frontend && npm run test` (52 component tests)
- Lint/typecheck: `cd frontend && npm run lint && npm run type-check`

## City Config Data
- City YAML configs: `data/cities/*.yaml` — 12 Indian cities
  - Bengaluru, Mumbai, Delhi NCR, Pune, Chennai, Hyderabad, Ahmedabad, Kolkata, Lucknow, Jaipur, Chandigarh, Bhubaneswar
- Each YAML defines: center coords, baselines, sector weights, constants, special zones, policies
- City boundary GeoJSONs: `data/cities/*.geojson`

## Sectors (7 India-specific)
`it_ites`, `manufacturing`, `real_estate`, `trade_hospitality`, `transport_logistics`, `informal`, `public_admin`

## Architecture Patterns

### Dependency Injection: `overlay_fn`
The engine no longer imports from `app/`. Instead, `run_simulation()` and `GridFactory.initialize()` accept an optional `overlay_fn` callback. The app layer injects `generate_overlay` at call time:
```python
# In app/ws/simulation.py:
async for frame in run_simulation(params, boundary, ..., overlay_fn=generate_overlay):
```
This keeps the engine free of app-layer imports and testable in isolation.

### Dependency Injection: `explainability_fn`
Similarly, `synthesize_evidence()` in `engine/tertiary_loop.py` accepts `explainability_fn`. The app layer injects `build_explanation`. The engine gracefully handles failures from the callback without crashing.

### Deterministic Slum Detection
Slum zones are flagged via hash-based selection, not random:
```python
slum_flag = (np.array([hash(h) % 1000 for h in h3_indices]) / 1000.0 < slum_pct)
```
This ensures identical results across runs for the same city config.

## Security

### Path Traversal Sanitization
`CityConfig.load()` and `CityConfig.load_geojson()` validate `city_name` with `re.fullmatch(r'[a-zA-Z0-9_]+', city_name)` to prevent directory traversal attacks. Zone file paths in `grid.py` also reject `..` patterns.

### WebSocket Connection Limit
Configurable via `WS_MAX_CONNECTIONS` env var (default: 10). Exceeding the limit returns WebSocket close code 1013 (Try Again Later). See `app/config.py` → `ws_max_connections`.

## Conventions
- Python: Use NumPy vectorized ops, no Python loops over cells in sim engine
- TypeScript: strict mode, camelCase props, PascalCase components
- All API responses use `{ success, data, error, meta }` envelope
- Simulation engine: NO database writes mid-loop, batch-save only after completion
- Commit format: `type(scope): description` (e.g. `feat(engine): add primary loop`)

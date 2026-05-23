# MetroPulse — Implementation Plan

**Version:** 1.0.0  
**Total Est. Duration:** ~25 days  
**Parallel Tracks:** Frontend & Backend can run concurrently after M0.

---

## Phase 0 — Project Scaffold (Days 1–2)

### 0.1 Repository Setup
- Create monorepo structure:
  ```
  /metropulse
    /frontend          # Next.js 14 app
    /backend           # FastAPI Python app
    /supabase          # Migration files
    /docs              # Architecture diagrams, API docs
    /scripts           # Dev utility scripts
    /tests             # Integration & E2E tests
    .github/workflows/ # CI/CD pipelines
  ```
- Initialize git repo, add `.gitignore` for Node + Python + env files

### 0.2 Backend Scaffold
- Initialize Python project: `pyproject.toml`, `requirements.txt`, `venv`
- Install: `fastapi`, `uvicorn[standard]`, `numpy`, `scipy`, `h3`, `httpx`, `websockets`, `supabase-py`, `openai`, `pydantic`, `pytest`, `pytest-asyncio`, `locust`
- Create FastAPI app entrypoint (`main.py`) with health check endpoint
- Set up logging (structured JSON logs) and CORS middleware (allow Vercel origin)
- Create `app/config.py` for env-based settings (pydantic-settings)

### 0.3 Frontend Scaffold
- `npx create-next-app@14 frontend --typescript --app --src-dir --import-alias "@/*"`
- Install: `deck.gl`, `@deck.gl/extensions`, `@deck.gl/layers`, `h3-js`, `mapbox-gl`, `react-map-gl`, `@tremor/react`, `tailwindcss`, `react-markdown`, `zustand`, `date-fns`
- Enable TypeScript strict mode in `tsconfig.json`
- Set up Tailwind config with MetroPulse theme colors (dark palette)
- Create `.env.local` template with `NEXT_PUBLIC_MAPBOX_TOKEN`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_API_URL`

### 0.4 Supabase Database
- Create Supabase project
- Write initial migration (`/supabase/migrations/001_schema.sql`) with all tables from SPEC §3.5
- Enable `pgvector` extension
- Create seed data: NYC metro region with boundary GeoJSON, baseline metrics
- Write migration for case_studies table with `pgvector` index
- Add Row Level Security policies

### 0.5 CI/CD Pipeline
- Create `.github/workflows/ci.yml`:
  - Backend: `pip install → pytest`
  - Frontend: `npm ci → npm run lint → npm run type-check → npm run test`
  - Deploy job (main only): `flyctl deploy` + `vercel --prod`

### 0.6 Project Documentation
- Create AGENTS.md for opencode context
- Create README.md with setup instructions
- Create `scripts/dev.sh` / `scripts/dev.ps1` for local dev startup

**Dependencies:** None  
**Review Gate:** All services start locally, DB migrations run, CI passes on empty project

---

## Phase 1 — Simulation Engine (Days 3–7)

### 1.1 H3 Grid Utilities (Day 3)
- File: `backend/engine/grid.py`
- Implement:
  - `GridState` class wrapping NumPy arrays for cell-level state
  - `GridState.initialize(region_boundary: GeoJSON, params: SimulationParams)`
    - Compute all H3 cells inside boundary at resolution 8 via `h3.polyfill()`
    - Initialize `E`, `K`, `R`, `T` arrays from baseline data
    - Build neighbor index for distance calculations
  - Helper: Haversine distance between any two H3 cell centers
  - `get_zone_cells(zone_geojson)` → list of H3 indices (for public works boost)

**Testing:**
- Test `polyfill` returns expected cell count for known boundary
- Test neighbor indexing returns correct adjacency
- Test Haversine distance accuracy against known coordinates

### 1.2 Primary Loop — Direct Impacts (Day 4)
- File: `backend/engine/primary_loop.py`
- Implement:
  ```python
  def step(state: GridState, params: SimulationParams) -> GridState:
  ```
  - Capital shock from FDI per sector: `ΔK_sector = FDI_rate × sector_weight × K(t-1)`
  - Aggregate sector shocks into total `ΔK` per cell
  - Employment response: `ΔE = α × ΔK × employment_elasticity`
  - Public works zone boost (if present): `boost = β × exp(-d / λ)` applied to K
  - All operations are vectorized NumPy — no Python loops over cells

**Testing:**
- Test with zero FDI → no state change
- Test with +100% tech FDI → verify K increases proportionally
- Test public works boost decays with distance
- Test NaN/Inf does not appear in output

### 1.3 Secondary Loop — Cascading Effects (Day 5)
- File: `backend/engine/secondary_loop.py`
- Implement:
  ```python
  def step(state: GridState, params: SimulationParams) -> GridState:
  ```
  - Real estate index cascade: `ΔR = γ × sum_neighbors[ΔK × exp(-d / λ_R)]`
  - Transit congestion adjustment: `ΔT = δ × ΔE / capacity`
  - Clamp `R` to [0.0, 2.0], `T` to [0.0, 1.0]
  - Compute aggregate metrics per step:
    - `GDP_delta = Σ(K(t) - K(0)) / Σ(K(0))`
    - `Unemployment = 1 - (ΣE(t) / ΣE(0)) × baseline_unemployment`
    - `RealEstateIdx = mean(R)`
    - `TransitCongestion = mean(T)`

**Testing:**
- Test clamping: overflow values are capped
- Test cascade spread: distant cells from capital change have smaller R delta
- Test aggregate metrics produce correct values for simple 2-cell grid

### 1.4 Runner & Serializer (Day 6)
- File: `backend/engine/runner.py`
- Implement:
  ```python
  async def run_simulation(params, db) -> AsyncGenerator[dict, None]:
      state = GridState.initialize(params)
      for month in range(1, params.horizon_months + 1):
          state = primary_loop.step(state, params)
          state = secondary_loop.step(state, params)
          frame = serializer.to_frame(state, month)
          yield frame
      await db.batch_save(state, params)
      insight = await tertiary_loop.synthesize(params, state)
      yield insight
  ```
- File: `backend/engine/serializer.py`
  - `to_frame(state, month)` → `SimulationFrame` dict
  - Convert NumPy arrays to list of `HexCellState` dicts
  - Include aggregate metrics

**Testing:**
- Test runner produces exactly `horizon_months` frames
- Test each frame has valid month, cells, and metrics
- Test batch_save is called exactly once after loop
- Performance test: 24-month run completes ≤ 1,500ms

### 1.5 Tertiary Loop — RAG & LLM (Day 7)
- File: `backend/engine/tertiary_loop.py`
- Implement:
  - `build_query(params, final_metrics)` → natural language query string
  - `retrieve_case_studies(query, db, top_k=5)` → pgvector similarity search
  - `build_prompt(params, metrics, case_studies)` → formatted prompt (SPEC §3.6 template)
  - `synthesize(prompt)` → call LLM API, return markdown text
  - Handle edge cases: LLM timeout (10s fallback), no case studies found

**Testing:**
- Test prompt construction with and without case studies
- Test LLM response is valid markdown
- Test timeout fallback returns static note

---

## Phase 2 — Backend API Layer (Days 8–10)

### 2.1 REST Endpoints
- File: `backend/app/routes/regions.py`
  - `GET /api/regions` — list regions from Supabase
  - `GET /api/regions/{id}/baseline` — fetch baseline for region
- File: `backend/app/routes/simulations.py`
  - `GET /api/simulations` — paginated list
  - `GET /api/simulations/{id}` — full result
  - `POST /api/simulations` — manual persist
- File: `backend/app/routes/health.py` — `GET /api/health`

### 2.2 WebSocket Handler
- File: `backend/app/ws/simulation.py`
- Implement:
  - Accept connection at `/ws/simulate`
  - Parse `START` message with `SimulationParams` validation (pydantic)
  - Validate GeoJSON in `publicWorksZone`
  - Spawn `run_simulation()` as async generator
  - Stream each frame as JSON `FRAME` message
  - Send `INSIGHT` message after frames complete
  - Send `DONE` message with `simulationId` after batch save confirms
  - Handle client disconnect: cancel simulation, do not batch-save
  - Error handling: send `ERROR` message for invalid params, timeouts, internal errors

### 2.3 Database Integration
- File: `backend/app/db.py`
  - Supabase client singleton
  - `batch_save(state, params)` — single `INSERT INTO simulations`
  - `get_region(id)` — region query
  - `get_baseline(region_id)` — baseline query
  - `search_case_studies(embedding)` — pgvector similarity search

### 2.4 Response Envelope Middleware
- All REST responses wrapped in `{ success, data, error, meta }` envelope
- Auto-inject request UUID, latency

**Testing:**
- Integration test: full WebSocket simulation → verify frames → verify DONE
- Test REST endpoints return correct status codes
- Test invalid GeoJSON returns 422 before WS opens

---

## Phase 3 — Frontend Map Shell (Days 9–11)

### 3.1 TypeScript Types
- File: `frontend/src/types/simulation.ts`
  - All interfaces matching SPEC §3.1 (`SimulationParams`, `HexCellState`, `SimulationFrame`, `AggregateMetrics`)
  - WebSocket message types (`SimulationRequest`, `FrameMessage`, `InsightMessage`, `ErrorMessage`, `DoneMessage`)
  - Type guards for runtime validation of incoming WS messages

### 3.2 Map Configuration
- File: `frontend/src/lib/mapConfig.ts`
  - Initial view state (NYC), Mapbox style (dark-v11), H3 resolution (8)
- File: `frontend/src/lib/colorScale.ts`
  - `deltaToRGBA(delta, height)` → `[r,g,b,a]` tuple

### 3.3 Deck.gl Viewport
- Component: `frontend/src/components/map/MapViewport.tsx`
  - `MapboxOverlay` from `@deck.gl/mapbox` or react-map-gl with Deck.GL
  - Dark base map
  - Orbit controls enabled (pitch, bearing, zoom)
  - Responsive container
- Component: `frontend/src/components/map/HexLayer.tsx`
  - `H3HexagonLayer` with `extruded: true`
  - Height encoding: `E(c,t)` → visual elevation
  - Color encoding: `deltaToRGBA(delta, height)`
  - Target ≥ 45 FPS during camera manipulation

### 3.4 Drawing Toolbar
- Component: `frontend/src/components/map/DrawingToolbar.tsx`
  - Point mode (pin drop)
  - Polygon mode (click-to-vertex)
  - Clear/reset button
  - Output: GeoJSON feature stored in state

**Testing:**
- Visual: verify hex grid renders over NYC
- Visual: verify color encoding updates with mock data
- Test: Polygon draw produces valid GeoJSON

---

## Phase 4 — WebSocket Integration (Days 11–13)

### 4.1 WebSocket Client
- File: `frontend/src/lib/ws.ts`
  - `WebSocketClient` singleton class
  - Connect, disconnect, send methods
  - Message routing: `onFrame`, `onInsight`, `onError`, `onDone` callbacks
  - Exponential backoff reconnect (1s → 2s → 4s → 8s → max 30s)
  - Max 5 retry attempts → error toast
- File: `frontend/src/components/shared/WebSocketProvider.tsx`
  - React context providing WS connection state
  - `useWebSocket()` hook for child components
  - Manages connection lifecycle (connect on mount, disconnect on unmount)

### 4.2 State Management
- Store: simulation state with Zustand or Context + useReducer
  - `frames: SimulationFrame[]` — accumulated frame history
  - `currentFrame: SimulationFrame | null` — latest frame
  - `insight: string | null` — latest insight markdown
  - `status: 'idle' | 'running' | 'done' | 'error'`
  - `error: string | null`
  - Actions: `startSimulation(params)`, `receiveFrame(frame)`, `receiveInsight(markdown)`, `reset()`

### 4.3 Metric Panel
- Component: `frontend/src/components/dashboard/MetricPanel.tsx`
  - Four Tremor `LineChart` components
  - X-axis: month (shared across charts)
  - Data source: `frames[]` from store, mapped to per-metric series
  - Real-time update as frames arrive
  - Empty state: "Run a simulation to see metrics"

**Testing:**
- Integration: start simulation → verify 24 frames received → charts rendered
- Test: reconnect after disconnect resumes correctly
- Test: error toast on max retries exceeded

---

## Phase 5 — Parameter Panel & Controls (Days 13–15)

### 5.1 Region Selector
- Fetch regions from `GET /api/regions` on mount
- Dropdown component with region name + city
- On select: update viewport to region center, load baseline

### 5.2 FDI Sliders
- Component: `frontend/src/components/controls/FDISliders.tsx`
  - Three sliders: Tech, Manufacturing, Real Estate
  - Range: -100% to +100%, step 1
  - Color-coded: red (negative) → gray (0) → green (positive)
  - Reset to zero button per slider

### 5.3 Public Works Zone Drawing
- Integrated into `DrawingToolbar.tsx` (from Phase 3)
- Drawn polygon/point stored in simulation params state
- Visual indicator on map (semi-transparent overlay)

### 5.4 Temporal Slider
- Component: `frontend/src/components/controls/TemporalSlider.tsx`
  - Discrete options: 6, 12, 24, 60 months
  - Styled as segmented button group

### 5.5 Parameter Panel Shell
- Component: `frontend/src/components/controls/ParameterPanel.tsx`
  - Composes all controls: region selector, FDISliders, zone drawing, temporal slider
  - "Run Simulation" button (disabled if WebSocket not connected)
  - Validation: at least one FDI value non-zero OR zone drawn
  - Loading state with `LoadingOverlay` during simulation

**Testing:**
- Test: all sliders update state correctly
- Test: "Run Simulation" disabled when no params changed
- Test: region change resets simulation state

---

## Phase 6 — RAG Pipeline & AI Panel (Days 16–18)

### 6.1 Case Study Embeddings
- Script: `/scripts/seed_case_studies.py`
  - Load case study dataset (manually curated ~20–30 urban policy cases)
  - Generate embeddings via OpenAI text-embedding-3-small
  - Insert into `case_studies` table with tags
- Verify pgvector similarity search returns relevant results

### 6.2 LLM Integration
- File: `backend/engine/tertiary_loop.py` (completed in Phase 1)
- Integration test: simulation → RAG → LLM → markdown insight

### 6.3 AI Insight Panel
- Component: `frontend/src/components/dashboard/AIInsightPanel.tsx`
  - Appears when `insight` is non-null in store
  - Renders markdown via `react-markdown`
  - Streaming effect: simulate character-by-character reveal (or chunk-based)
  - Collapsible sidebar panel (pinnable)
  - Empty state: hidden or "AI analysis will appear here"
  - Loading state: pulsing skeleton during INSIGHT streaming

**Testing:**
- Test: INSIGHT message renders valid markdown
- Test: panel collapses/expands
- Test: multiple simulations → insight updates correctly

---

## Phase 7 — Loading & Transition States (Day 18)

### 7.1 LoadingOverlay
- Component: `frontend/src/components/shared/LoadingOverlay.tsx`
  - Glassmorphism semi-transparent backdrop
  - Pulsing MetroPulse logo + "Simulating…" text
  - Shows frame count: "Frame 7 / 24"
  - Auto-dismisses on DONE or ERROR message

### 7.2 Error States
- WebSocket error toast (via Tremor `Toast` or custom)
- Simulation error display (inline warning in ParameterPanel)
- Map tile load fallback (OpenStreetMap tiles)
- Empty states for MetricPanel, AIInsightPanel

### 7.3 Transition Animations
- Smooth hex layer transitions between frames (Deck.gl `transitionDuration`)
- Chart update animation (Tremor default)
- Insight panel slide-in from right

---

## Phase 8 — Polish & Performance (Days 19–21)

### 8.1 WebSocket Compression
- Enable `permessage-deflate` extension on both server and client
- Verify frame size reduction (target: 60%+ reduction)

### 8.2 Deck.gl Performance
- Use `binary` attribute transport for hex layer (avoid JS object serialization per frame)
- Enable `fp64` mode only if needed
- Limit hex count via LOD (Level of Detail) at low zoom levels
- Profile with Chrome DevTools Performance tab → target ≥ 45 FPS

### 8.3 Backend Optimization
- Profile simulation loops for NumPy vectorization bottlenecks
- Pre-compute neighbor distance matrices (cache for same region)
- Ensure async generators yield without blocking event loop
- Verify 24-month horizon ≤ 1,500ms with `pytest-benchmark`

### 8.4 Zero Console Warnings
- ESLint: no `console.warn` in production builds
- Remove all debug logging from frontend
- Ensure all dependencies are compatible (no React strict mode warnings)

### 8.5 Error Recovery
- Finalize all error handling from SPEC §9
- Test: disconnect WebSocket mid-stream → reconnect → resume
- Test: invalid params → error toast → user can re-submit

---

## Phase 9 — Testing (Days 21–23)

### 9.1 Unit Tests (Backend)
- `tests/unit/test_grid.py`: Grid initialization, neighbor indexing
- `tests/unit/test_primary_loop.py`: FDI shock, public works boost
- `tests/unit/test_secondary_loop.py`: Real estate cascade, congestion
- `tests/unit/test_serializer.py`: NumPy arrays to JSON frames
- `tests/unit/test_color_scale.py`: Boundary conditions

### 9.2 Unit Tests (Frontend)
- TypeScript type guard tests
- `colorScale.ts` boundary tests with Jest
- WS message parsing/validation tests

### 9.3 Integration Tests
- `tests/integration/test_ws_simulation.py`:
  - Full run with test WebSocket client
  - Verify frame count per horizon (6, 12, 24, 60)
  - Verify batch_save writes exactly one row
  - Verify INSIGHT message is valid markdown
- `tests/integration/test_rest_endpoints.py`:
  - Response time < 200ms (p95)
  - Correct status codes for all endpoints
  - Pagination correctness

### 9.4 Performance Tests
- `tests/performance/test_sim_duration.py`: 24-month horizon < 1,500ms
- `tests/performance/test_concurrent_sims.py`: 10 concurrent users
- Locust load test script in `/tests/load/locustfile.py`

### 9.5 End-to-End Tests
- Playwright script in `tests/e2e/simulation.spec.ts`:
  - Open app → verify map loads
  - Set FDI sliders → draw polygon → run simulation
  - Assert metric charts populate
  - Assert insight panel renders markdown

---

## Phase 10 — Deployment (Days 23–25)

### 10.1 Backend Deployment (Fly.io)
- Dockerfile with Python 3.11 slim, uvicorn CMD
- `fly.toml` config (2 vCPU, 2GB RAM, iad region)
- Environment variables: Supabase URL, Supabase key, OpenAI key
- Deploy: `flyctl deploy --remote-only`

### 10.2 Frontend Deployment (Vercel)
- Connect GitHub repo to Vercel
- Set environment variables in Vercel dashboard
- Configure custom domain (api.metropulse.app, app.metropulse.app)
- Enable automatic HTTPS

### 10.3 Database Production Migration
- Run Supabase migrations on production DB
- Seed case studies into production vector store
- Row Level Security verified

### 10.4 CI/CD Finalization
- Verify GitHub Actions workflows deploy on main merge
- Add status badges to README
- Configure deployment previews for PRs

### 10.5 Load Testing
- Run Locust test against production/staging
- Verify 10 concurrent simulations complete within spec
- Verify REST endpoints respond < 200ms p95

---

## Summary Dependency Graph

```
M0 (Scaffold)
 ├── M1 (Sim Engine) ──→ M2 (Backend API) ──→ M4 (Controls)
 └── M3 (Map Shell) ────→ M5 (WebSocket) ───→ M6 (RAG/AI Panel)
                                       └────→ M7 (Polish) → M8 (Testing) → M9 (Deploy)
```

**Parallelizable tracks:**
- Track A (Backend): M1 → M2 (→ M4 integration point)
- Track B (Frontend): M3 → M4 (→ M5 integration point)
- M5 (WebSocket) is the merge point where both tracks converge

---

## Key Risk Mitigation

| Risk | Impact | Mitigation | Phase |
|---|---|---|---|
| H3 polyfill too slow for large regions | 500ms+ init | Cache cell indices per region in DB; precompute ✅ | M1 |
| WebSocket frame JSON too large | >100KB per frame | Enable `permessage-deflate`; use binary transfer ✅ | M7 |
| LLM API latency blocks DONE message | User waits for insight | Send DONE immediately, stream INSIGHT as separate message ✅ | M2 |
| NumPy loop not fast enough for 10K cells | >62ms/step | Vectorize all ops; use `einsum` for neighbor distance ✅ | M1 |
| Mapbox GL license cost | $200+/month | Use Mapbox free tier + OpenStreetMap fallback ✅ | M3 |

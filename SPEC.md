# MetroPulse — Engineering Specification

**Project:** AI-Powered Macro-Urban Digital Twin Sandbox  
**Version:** 1.0.0  
**Status:** Pre-production  
**Author:** 3rd Year CSE Student  
**Target:** Production Internship Portfolio

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Module Specifications](#3-module-specifications)
   - 3.1 [Frontend — Next.js App](#31-frontend--nextjs-app)
   - 3.2 [Simulation Engine — Backend Core](#32-simulation-engine--backend-core)
   - 3.3 [WebSocket Streaming Layer](#33-websocket-streaming-layer)
   - 3.4 [REST Analytics API](#34-rest-analytics-api)
   - 3.5 [Database Layer — Supabase PostgreSQL](#35-database-layer--supabase-postgresql)
   - 3.6 [Vector Store & RAG Pipeline](#36-vector-store--rag-pipeline)
4. [Data Models & Schemas](#4-data-models--schemas)
5. [Simulation Logic — Mathematical Specification](#5-simulation-logic--mathematical-specification)
6. [API Contracts](#6-api-contracts)
7. [UI Component Breakdown](#7-ui-component-breakdown)
8. [Non-Functional Requirements & Constraints](#8-non-functional-requirements--constraints)
9. [Error Handling & Edge Cases](#9-error-handling--edge-cases)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment Plan](#11-deployment-plan)
12. [Development Milestones](#12-development-milestones)

---

## 1. Project Summary

MetroPulse is an interactive, real-time digital twin sandbox that models macro-urban policies and economic interventions. Users inject simulation parameters (financial shocks, geospatial interventions, temporal scales) and the system computes and visualizes cascading geospatial, financial, and infrastructural consequences across a configurable multi-year horizon via a hardware-accelerated 3D dashboard.

### Core Differentiators

- **Real-time 3D hexagonal heatmapping** using WebGL-accelerated Deck.gl layers.
- **Agent-based cascading simulation** running entirely in-memory to eliminate mid-loop I/O bottlenecks.
- **RAG-powered AI case synthesis** that surfaces historical urban precedent from a vector store, streamed as markdown insights.
- **Sub-1.5-second** full 24-month simulation horizon computation.

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND                       │
│   Deck.gl (WebGL Map)  |  Tremor Charts  |  AI Panel      │
└──────────────▲───────────────────────────▲─────────────────┘
               │ HTTP REST                 │ WebSocket (WSS)
               │ (Analytics Queries)       │ (Live Sim Stream)
┌──────────────┴───────────────────────────┴─────────────────┐
│             FASTAPI  /  SPRING BOOT BACKEND                │
│   Simulation Core  |  REST Router  |  WS Manager          │
└──────────────▲───────────────────────────▲─────────────────┘
               │                           │
    ┌──────────┴──────────┐    ┌───────────┴──────────┐
    │  SUPABASE POSTGRES  │    │  VECTOR DB (pgvector) │
    │  Historical Trends  │    │  Case Studies (RAG)   │
    │  Region Metadata    │    │  Embeddings Index     │
    └─────────────────────┘    └──────────────────────┘
```

### Technology Choices

| Layer | Technology | Rationale |
|---|---|---|
| Frontend Framework | Next.js 14 (App Router) | SSR, file-based routing, streaming RSC support |
| 3D Map Rendering | Deck.gl + Mapbox GL JS | WebGL-accelerated, supports H3 hexagonal layers |
| Dashboard UI | Tremor + Tailwind CSS | Composable chart components, utility-first styling |
| Primary Backend | FastAPI (Python) | Async I/O, native NumPy/SciPy matrix ops, type hints |
| Concurrent Agents | Spring Boot (optional) | Multi-threaded agent simulation if agent count > 5,000 |
| Database | Supabase (PostgreSQL) | Managed Postgres, real-time subscriptions, Row Level Security |
| Vector Store | pgvector extension | Embedding similarity search within existing Supabase DB |
| LLM API | Anthropic Claude / OpenAI | Qualitative case synthesis and streaming markdown output |
| Infra / Hosting | Vercel (frontend) + Railway or Fly.io (backend) | Zero-config deploys, environment variable management |

---

## 3. Module Specifications

### 3.1 Frontend — Next.js App

**Directory Structure**

```
/app
  /page.tsx                  # Root: renders the sandbox shell
  /api/simulate/route.ts     # Thin proxy to backend REST
/components
  /map
    MapViewport.tsx           # Deck.gl canvas + Mapbox base layer
    HexLayer.tsx              # H3HexagonLayer configuration
    DrawingToolbar.tsx        # Polygon draw / pin drop controls
  /controls
    ParameterPanel.tsx        # Slider + zone input panel
    TemporalSlider.tsx        # Projection horizon slider
    FDISliders.tsx            # Per-sector FDI adjustment (-100% → +100%)
  /dashboard
    MetricPanel.tsx           # Tremor LineChart grid
    AIInsightPanel.tsx        # Streaming markdown renderer
  /shared
    WebSocketProvider.tsx     # Context + hook for WS connection
    LoadingOverlay.tsx        # Glassmorphism loading state
/lib
  ws.ts                       # WebSocket client singleton
  mapConfig.ts                # Mapbox token, initial viewport
  colorScale.ts               # Delta → RGB interpolation (red/amber/green)
/types
  simulation.ts               # Shared TypeScript interfaces
```

**State Management**

Use React Context + `useReducer` for global simulation state. Zustand is acceptable if cross-component subscriptions become complex.

```typescript
// types/simulation.ts
export interface SimulationParams {
  fdi: {
    tech: number;         // -100 to 100
    manufacturing: number;
    realEstate: number;
  };
  publicWorksZone: GeoJSON.Polygon | GeoJSON.Point | null;
  horizonMonths: number;  // 6 | 12 | 24 | 60
}

export interface HexCellState {
  h3Index: string;         // H3 cell identifier
  economicActivity: number; // 0.0 – 1.0 (normalized)
  delta: number;            // Change relative to baseline (-1.0 – 1.0)
  jobDensity: number;       // Jobs per km²
  realEstateIndex: number;  // Relative land value
  congestion: number;       // Transit load 0.0 – 1.0
}

export interface SimulationFrame {
  month: number;
  timestamp: string;
  cells: HexCellState[];
  metrics: AggregateMetrics;
}

export interface AggregateMetrics {
  gdpDelta: number;
  unemploymentRate: number;
  realEstateIndex: number;
  transitCongestion: number;
}
```

**Map Viewport Configuration**

```typescript
// lib/mapConfig.ts
export const INITIAL_VIEW_STATE = {
  longitude: -73.935242,  // Default: New York (configurable)
  latitude: 40.730610,
  zoom: 11,
  pitch: 45,
  bearing: 0,
};

export const MAP_STYLE = "mapbox://styles/mapbox/dark-v11";
export const H3_RESOLUTION = 8; // ~500m x 500m cells
```

**HexLayer Color Encoding**

```typescript
// lib/colorScale.ts
// delta: -1.0 = full red, 0 = amber, +1.0 = full green
export function deltaToRGBA(delta: number, height: number): [number, number, number, number] {
  if (delta > 0.1) return [34, 197, 94, 200];   // green-500
  if (delta < -0.1) return [239, 68, 68, 200];   // red-500
  return [251, 191, 36, 200];                     // amber-400
}
```

---

### 3.2 Simulation Engine — Backend Core

**Language:** Python 3.11+ with FastAPI. NumPy used for all matrix operations.

**In-Memory State Rule:** The simulation loop must never issue a database write mid-step. All state is held in NumPy arrays and Python dicts; batch-saved to Supabase only after the full horizon computation completes.

**Core Engine Modules**

```
/engine
  __init__.py
  models.py          # Pydantic input/output schemas
  grid.py            # H3 cell initialization and spatial indexing
  primary_loop.py    # Direct employment + capital allocation
  secondary_loop.py  # Real estate decay + transit congestion
  tertiary_loop.py   # RAG query + LLM case synthesis
  runner.py          # Orchestrates loops per monthly step
  serializer.py      # Converts NumPy state → JSON frames
```

**Runner Orchestration**

```python
# engine/runner.py (pseudocode)
async def run_simulation(params: SimulationParams) -> AsyncGenerator[SimulationFrame, None]:
    state = GridState.initialize(params)  # All in-memory, no DB write

    for month in range(1, params.horizon_months + 1):
        state = primary_loop.step(state, params)
        state = secondary_loop.step(state, params)
        frame = serializer.to_frame(state, month)
        yield frame  # Streamed over WebSocket

    await db.batch_save(state)  # Single write after loop completion
    insight = await tertiary_loop.synthesize(params, state)
    yield insight
```

**Performance Targets**

- 24-month horizon: full computation ≤ 1,500ms
- Per-month step computation: ≤ 62ms (1,500ms / 24 steps)
- Max concurrent simulations: 10 simultaneous users (horizontal scaling via Fly.io)

---

### 3.3 WebSocket Streaming Layer

**Protocol:** WSS (WebSocket Secure)  
**Endpoint:** `wss://<backend-host>/ws/simulate`

**Message Format**

All messages are JSON. The backend streams one message per simulation month, plus a terminal `insight` message.

```typescript
// Upstream: client → server (sent once on connection)
interface SimulationRequest {
  type: "START";
  params: SimulationParams;
}

// Downstream: server → client (one per month step)
interface FrameMessage {
  type: "FRAME";
  payload: SimulationFrame;
}

// Downstream: server → client (final, after all frames)
interface InsightMessage {
  type: "INSIGHT";
  markdown: string;  // Streamed token-by-token using SSE within WS or chunked
}

// Downstream: server → client
interface ErrorMessage {
  type: "ERROR";
  code: string;
  message: string;
}

// Downstream: server → client (after batch DB save completes)
interface DoneMessage {
  type: "DONE";
  simulationId: string;
}
```

**Client Reconnection Logic**

Implement exponential backoff reconnect in `WebSocketProvider.tsx`: 1s → 2s → 4s → 8s → max 30s. After 5 failed attempts, surface a user-facing error toast.

---

### 3.4 REST Analytics API

Used for non-real-time queries: loading historical baselines, fetching past simulation results, and region metadata.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/regions` | List all available region polygons with metadata |
| `GET` | `/api/regions/{id}/baseline` | Fetch baseline economic state for a region |
| `GET` | `/api/simulations` | List past simulation runs (paginated) |
| `GET` | `/api/simulations/{id}` | Fetch full result of a past simulation |
| `POST` | `/api/simulations` | Persist a simulation result manually |
| `GET` | `/api/health` | Health check (returns 200 + version) |

**Response Envelope**

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "requestId": "uuid",
    "latencyMs": 42
  }
}
```

All endpoints must respond in ≤ 200ms for standard state retrieval (p95).

---

### 3.5 Database Layer — Supabase PostgreSQL

**Schema**

```sql
-- Regions table: defines spatial extent of each simulated metro area
CREATE TABLE regions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  city        TEXT NOT NULL,
  country     TEXT NOT NULL,
  boundary    JSONB NOT NULL,  -- GeoJSON Polygon (strict GeoJSON spec)
  population  INTEGER,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Baseline metrics: economic snapshot per region per period
CREATE TABLE region_baselines (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  region_id       UUID REFERENCES regions(id) ON DELETE CASCADE,
  recorded_at     DATE NOT NULL,
  gdp_index       NUMERIC(10,4),
  unemployment    NUMERIC(5,4),
  real_estate_idx NUMERIC(10,4),
  transit_load    NUMERIC(5,4)
);

-- Simulation runs: persisted after each completed simulation
CREATE TABLE simulations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  region_id       UUID REFERENCES regions(id),
  params          JSONB NOT NULL,   -- SimulationParams as JSON
  horizon_months  INTEGER NOT NULL,
  result_summary  JSONB,            -- AggregateMetrics at final month
  cell_states     JSONB,            -- Final HexCellState[] snapshot
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_simulations_region ON simulations(region_id);
CREATE INDEX idx_baselines_region   ON region_baselines(region_id);
```

**Anti-Pattern Constraint:** The simulation engine MUST NOT call any Supabase write endpoint during the active monthly step loop. All writes are deferred to a single `batch_save()` call invoked after the loop terminates.

---

### 3.6 Vector Store & RAG Pipeline

**Extension:** `pgvector` on the Supabase PostgreSQL instance.

**Schema**

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE case_studies (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  city        TEXT NOT NULL,
  year        INTEGER,
  description TEXT NOT NULL,          -- Full case study text
  tags        TEXT[],                  -- e.g. ['tech_downturn', 'real_estate', 'transit']
  embedding   vector(1536),           -- OpenAI text-embedding-3-small output
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON case_studies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**RAG Query Flow**

```
1. After simulation completes, construct a query string from final params:
   "Tech FDI -40%, 24-month horizon, public works in downtown core"

2. Embed query using the same embedding model (text-embedding-3-small)

3. Run similarity search:
   SELECT title, description, city, year
   FROM case_studies
   ORDER BY embedding <=> $query_vector
   LIMIT 5;

4. Inject retrieved excerpts + simulation outcome into LLM prompt

5. Stream LLM response (markdown bullets) back to frontend via the
   existing WebSocket connection as an INSIGHT message
```

**LLM Prompt Template**

```
You are an urban economics analyst. A simulation has been run with the following parameters:
<params>{{ simulation_params_json }}</params>

The simulation produced these outcomes after {{ horizon }} months:
<outcome>{{ final_metrics_json }}</outcome>

Historical precedents from similar urban interventions:
<precedents>
{{ case_study_excerpts }}
</precedents>

Provide a concise analysis in 5–7 markdown bullet points covering:
- Key risks identified from the historical precedents
- Sectors most vulnerable given the parameters
- Any counter-intuitive outcomes to watch for
- One recommended policy adjustment based on the data
```

---

## 4. Data Models & Schemas

### GeoJSON Compliance

All geospatial data must strictly conform to RFC 7946 (GeoJSON). Coordinate order is `[longitude, latitude]`.

```typescript
// Valid Public Works Zone representations
type PublicWorksZone =
  | { type: "Point"; coordinates: [number, number] }
  | { type: "Polygon"; coordinates: [number, number][][] };
```

### H3 Grid Resolution

| Resolution | Avg Cell Area | Edge Length | Use |
|---|---|---|---|
| 7 | ~5.2 km² | ~1,220m | City-wide overview |
| **8** | **~0.74 km²** | **~461m** | **Target (≈500m)** |
| 9 | ~0.1 km² | ~174m | Neighborhood detail |

Resolution 8 is the default. Zoom-adaptive resolution switching (7 at zoom < 10, 8 at zoom 10–13, 9 at zoom > 13) is a stretch goal.

---

## 5. Simulation Logic — Mathematical Specification

### 5.1 Grid Initialization

For each H3 cell `c` in the region at `t = 0`:

```
E(c, 0) = baseline_employment_density(c)       [jobs/km²]
K(c, 0) = baseline_capital_allocation(c)        [normalized 0–1]
R(c, 0) = baseline_real_estate_index(c)         [normalized 0–1]
T(c, 0) = baseline_transit_congestion(c)        [normalized 0–1]
```

### 5.2 Primary Loop — Direct Impacts (per month step `t`)

**Capital Shock from FDI:**

```
ΔK_sector(c, t) = FDI_rate_sector × sector_weight(c) × K(c, t-1)
K(c, t) = K(c, t-1) + Σ_sector ΔK_sector(c, t)
```

**Employment Response:**

```
ΔE(c, t) = α × ΔK(c, t) × employment_elasticity(c)
E(c, t) = E(c, t-1) + ΔE(c, t)
```

Where `α = 0.6` is the capital-to-employment multiplier (calibrated from baseline data).

**Public Works Zone Boost (if zone is active):**

```
boost(c) = β × e^(-d(c, zone_centroid) / λ)
```

Where:
- `β = 0.3` is the maximum direct boost factor
- `d(c, zone_centroid)` is the Haversine distance in km from cell center to zone centroid
- `λ = 2.0` is the distance decay constant in km

```
K(c, t) += boost(c)     # Applied on top of FDI shock
```

### 5.3 Secondary Loop — Cascading Effects

**Real Estate Index (distance decay from capital change):**

```
ΔR(c, t) = γ × Σ_{c' ∈ neighbors(c)} [ΔK(c', t) × e^(-d(c, c') / λ_R)]
R(c, t) = clamp(R(c, t-1) + ΔR(c, t), 0.0, 2.0)
```

Where `γ = 0.15` and `λ_R = 3.5` km.

**Transit Congestion Adjustment:**

```
ΔT(c, t) = δ × ΔE(c, t) / capacity(c)
T(c, t) = clamp(T(c, t-1) + ΔT(c, t), 0.0, 1.0)
```

Where `δ = 0.08` is the employment-to-congestion sensitivity.

### 5.4 Aggregate Metrics (per step)

```
GDP_delta(t) = Σ_c [K(c,t) - K(c,0)] / Σ_c K(c,0)
Unemployment(t) = 1 - (Σ_c E(c,t) / Σ_c E(c,0)) × baseline_unemployment_rate
RealEstateIdx(t) = mean_c R(c,t)
TransitCongestion(t) = mean_c T(c,t)
```

### 5.5 Cell Delta (for color encoding)

```
delta(c, t) = clamp((K(c,t) - K(c,0)) / K(c,0), -1.0, 1.0)
height(c, t) = normalize(E(c,t))   # Used for 3D prism height in Deck.gl
```

---

## 6. API Contracts

### 6.1 WebSocket: Start Simulation

**Client → Server (on connection open):**

```json
{
  "type": "START",
  "params": {
    "fdi": {
      "tech": -40,
      "manufacturing": 10,
      "realEstate": -20
    },
    "publicWorksZone": {
      "type": "Polygon",
      "coordinates": [[[-73.98, 40.75], [-73.97, 40.75], [-73.97, 40.76], [-73.98, 40.76], [-73.98, 40.75]]]
    },
    "horizonMonths": 24
  }
}
```

**Server → Client (per month frame):**

```json
{
  "type": "FRAME",
  "payload": {
    "month": 3,
    "timestamp": "2025-03-01T00:00:00Z",
    "cells": [
      {
        "h3Index": "882a100d2dfffff",
        "economicActivity": 0.72,
        "delta": -0.18,
        "jobDensity": 4200,
        "realEstateIndex": 0.88,
        "congestion": 0.61
      }
    ],
    "metrics": {
      "gdpDelta": -0.034,
      "unemploymentRate": 0.067,
      "realEstateIndex": 0.91,
      "transitCongestion": 0.58
    }
  }
}
```

### 6.2 REST: GET /api/regions

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Manhattan",
      "city": "New York",
      "country": "US",
      "population": 1600000,
      "boundary": { "type": "Polygon", "coordinates": [[...]] }
    }
  ]
}
```

---

## 7. UI Component Breakdown

### 7.1 Parameter Panel

| Control | Type | Range / Options | Default |
|---|---|---|---|
| Tech FDI | Slider | -100% to +100% | 0% |
| Manufacturing FDI | Slider | -100% to +100% | 0% |
| Real Estate FDI | Slider | -100% to +100% | 0% |
| Public Works Zone | Map draw tool | Polygon or Point | None |
| Projection Horizon | Slider | 6, 12, 24, 60 months | 12 |
| Region Selector | Dropdown | List from `/api/regions` | New York |

### 7.2 Map Viewport

- Dark base map (Mapbox dark-v11)
- H3HexagonLayer from Deck.gl with `extruded: true`
- Height encoding: `E(c, t)` normalized to `[0, 50000]` (elevation in meters, scaled visually)
- Color encoding: delta → RGB interpolation (see `colorScale.ts`)
- Orbit controls enabled (pitch, bearing, zoom)
- Drawing toolbar (react-map-gl-draw or deck.gl EditableGeoJsonLayer)
- Target: ≥ 45 FPS during camera manipulation

### 7.3 Metric Panel (Tremor LineCharts)

Four synchronized charts, each plotting the trailing history of monthly simulation frames:

| Chart | Y-Axis Label | Unit |
|---|---|---|
| GDP Delta | Change from baseline | % |
| Local Unemployment | Rate | % |
| Real Estate Index | Relative value | Index (0–2) |
| Transit Congestion | Load factor | 0–100% |

Charts update in real-time as frames arrive via WebSocket.

### 7.4 AI Insight Panel

- Appears after the `INSIGHT` WebSocket message begins streaming
- Renders markdown using `react-markdown`
- Typing animation effect using streamed token delivery
- Collapsible / pinnable to the right sidebar

---

## 8. Non-Functional Requirements & Constraints

| Requirement | Target | Notes |
|---|---|---|
| Simulation compute (24-month horizon) | ≤ 1,500ms | Backend; measured from request receipt to first DONE message |
| UI frame rate (3D map) | ≥ 45 FPS | During camera pan/rotate with active layer |
| REST API latency (p95) | ≤ 200ms | Standard state retrieval endpoints |
| WebSocket frame size | Compressed (deflate) | Per-frame JSON compressed via `permessage-deflate` extension |
| Geospatial standard | GeoJSON RFC 7946 | Enforced on all input/output coordinate data |
| Grid resolution | 500m × 500m (H3 res 8) | Configurable but defaults to res 8 |
| Max concurrent agents | 10,000 entities | In-memory agent pool; Spring Boot thread pool if needed |
| Max concurrent simulation users | 10 | Horizontal scale via container replicas |
| Storage | Supabase relational only | No secondary file-based storage for structured metadata |
| DB write during simulation loop | FORBIDDEN | All state in-memory; single batch save post-loop |
| Console warnings in production | Zero | ESLint rules enforced in CI |
| TypeScript strict mode | Enabled | `strict: true` in `tsconfig.json` |

---

## 9. Error Handling & Edge Cases

### Backend

| Scenario | Behavior |
|---|---|
| Invalid GeoJSON in `publicWorksZone` | Return HTTP 422 with field-level validation error before WebSocket is opened |
| `horizonMonths` outside allowed values | Clamp to nearest valid value (6/12/24/60); warn client |
| H3 cell has zero baseline population | Skip primary loop for that cell; maintain in grid for rendering |
| LLM API timeout (> 10s) | Send partial INSIGHT message with a fallback static note; do not block DONE |
| Vector DB returns 0 results | Proceed with LLM synthesis without precedents; note absence in prompt |
| Simulation takes > 3,000ms | Terminate, send ERROR message, do not batch-save |

### Frontend

| Scenario | Behavior |
|---|---|
| WebSocket connection dropped mid-stream | Reconnect with exponential backoff; replay last known frame |
| Map tile load failure | Fallback to OpenStreetMap raster tiles |
| Frame arrives with unexpected H3 resolution | Log warning, skip rendering that frame, continue |
| Simulation produces NaN in cell state | Replace with 0.0; surface a console warning (development only) |

---

## 10. Testing Strategy

### Unit Tests (pytest / Jest)

- All mathematical loop functions in `primary_loop.py`, `secondary_loop.py` must have unit tests verifying output ranges (e.g., no cell value exceeds bounds).
- TypeScript type guards on incoming WebSocket frames.
- Color scale function: test boundary conditions (delta = -1.0, 0.0, +1.0).

### Integration Tests

- Full simulation run via test WebSocket client: verify correct number of frames emitted for each horizon (6, 12, 24, 60 months).
- Verify batch-save writes exactly one row to `simulations` table after each run.
- REST endpoint response time assertions (< 200ms) via `pytest-benchmark`.

### Performance Tests

- Locust load test: 10 concurrent WebSocket simulation clients, 24-month horizon each. Assert p95 completion < 1,500ms.
- Deck.gl FPS test: Playwright + `stats.js` injected to assert > 45 FPS during programmatic camera orbit.

### End-to-End Tests

- Playwright: open app → set FDI sliders → draw polygon → run simulation → assert metric charts populate → assert insight panel renders markdown.

---

## 11. Deployment Plan

### Frontend (Vercel)

```bash
# Environment variables
NEXT_PUBLIC_MAPBOX_TOKEN=pk.ey...
NEXT_PUBLIC_WS_URL=wss://api.metropulse.app/ws
NEXT_PUBLIC_API_URL=https://api.metropulse.app
```

### Backend (Fly.io)

```toml
# fly.toml
app = "metropulse-api"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false

[[vm]]
  cpu_kind = "shared"
  cpus = 2
  memory_mb = 2048
```

### Database (Supabase)

- Enable `pgvector` extension via Supabase dashboard.
- Run schema migrations via `supabase db push` with migration scripts versioned in `/supabase/migrations/`.
- Enable Row Level Security on all tables; simulation reads are public, writes require service role key.

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml (abbreviated)
on: [push, pull_request]
jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ --tb=short
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run lint && npm run type-check && npm run test
  deploy:
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main'
    steps:
      - run: flyctl deploy --remote-only  # Backend
      - run: vercel --prod               # Frontend
```

---

## 12. Development Milestones

| Milestone | Deliverable | Est. Duration |
|---|---|---|
| M0 — Scaffold | Repo structure, CI pipeline, Supabase schema migrations, env config | 2 days |
| M1 — Map Shell | Dark-themed Deck.gl viewport with static H3 hex grid overlay | 3 days |
| M2 — Sim Engine v1 | Primary + secondary loops, in-memory runner, unit tests passing | 5 days |
| M3 — WebSocket Integration | Live frame streaming from backend to frontend; charts update in real-time | 3 days |
| M4 — Parameter Panel | All sliders wired, polygon draw tool, region selector connected to `/api/regions` | 2 days |
| M5 — RAG Pipeline | Case study embeddings loaded, pgvector search, LLM prompt wired | 3 days |
| M6 — AI Insight Panel | Streamed markdown rendering in UI, INSIGHT message integrated | 2 days |
| M7 — Polish & Performance | FPS optimizations, WebSocket compression, zero console warnings, README | 3 days |
| M8 — Deployment | Vercel + Fly.io live, public URL, load tests passing | 2 days |

**Total estimated:** ~25 days

---

## Appendix A — Parameter Constants Summary

| Symbol | Value | Description |
|---|---|---|
| α | 0.6 | Capital-to-employment multiplier |
| β | 0.3 | Public works zone direct boost factor |
| γ | 0.15 | Real estate cascade sensitivity |
| δ | 0.08 | Employment-to-congestion sensitivity |
| λ | 2.0 km | Public works distance decay constant |
| λ_R | 3.5 km | Real estate cascade decay constant |
| H3 res | 8 | Default hexagonal grid resolution |

---

## Appendix B — Glossary

| Term | Definition |
|---|---|
| H3 | Uber's hierarchical hexagonal geospatial indexing system |
| FDI | Foreign Direct Investment — capital inflows from external entities into a sector |
| RAG | Retrieval-Augmented Generation — LLM prompting enhanced with retrieved document context |
| Digital Twin | A computational model that mirrors the state and behavior of a real-world system |
| Distance Decay | The empirical phenomenon where influence diminishes as a function of distance |
| pgvector | A PostgreSQL extension enabling efficient vector similarity search |
| GeoJSON | An open standard for encoding geographic data structures in JSON (RFC 7946) |

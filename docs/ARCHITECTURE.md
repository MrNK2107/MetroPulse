# MetroPulse Architecture

MetroPulse is an interactive urban scenario sandbox. It combines natural-language scenario parsing, retrieved evidence, bounded coefficient adjustment, real-time contextual overlays, deterministic simulation loops, confidence scoring, and explainability.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript 5, Zustand 4, Tailwind CSS 3 |
| Map | deck.gl 9, MapLibre GL, H3 hexagonal grid |
| Charts | Tremor (AreaChart) |
| Backend | FastAPI, Python 3.11+, NumPy, spaCy |
| Database | Supabase PostgreSQL, pgvector |
| LLM | MiMo (mimo-v2.5-pro via OpenGateway), fallback to deterministic |
| Transport | WebSocket (primary), REST (health/regions/simulations) |

## Module Map

```
backend/
├── app/
│   ├── config.py              # Env-based settings (Supabase, LLM, realtime cadences)
│   ├── db.py                  # DatabaseClient: Supabase + in-memory fallback
│   ├── main.py                # FastAPI app, CORS, request logging middleware, API v1 routing
│   ├── rag/                   # RAG engine (retriever, evidence pack, coefficient extractor)
│   ├── realtime.py            # 6 connectors: News RSS, GDELT, mobility/jobs/land proxies, census
│   ├── realtime_models.py     # DataDomain, SourceStatus, SnapshotData
│   ├── routes/                # REST endpoints (health, regions, simulations, case_studies, realtime)
│   ├── simulation/
│   │   ├── confidence.py      # Weighted confidence formula
│   │   ├── explainability.py  # Top drivers with origins
│   │   └── overlay.py         # City-level signals → per-cell H3 modifiers
│   └── ws/
│       └── simulation.py      # WebSocket handler: orchestrates full pipeline
├── engine/
│   ├── config.py              # City YAML loader
│   ├── grid.py                # GridFactory: H3 tessellation + initialization
│   ├── models.py              # GridState dataclass (K, E, R, T, H, F, M + confidence arrays)
│   ├── nl_engine/             # Intent router (regex → spaCy → fallback)
│   ├── primary_loop.py        # Month-step: capital + employment shocks
│   ├── provenance.py          # Confidence decay constants
│   ├── runner.py              # Async simulation driver
│   ├── secondary_loop.py      # Month-step: cascading effects (RE, transit, migration)
│   ├── serializer.py          # GridState → JSON frame
│   ├── simulation_explainability.py  # Driver breakdown per metric
│   ├── tertiary_loop.py       # Post-sim evidence synthesis
│   └── translator.py          # Plain-language output with ₹ amounts
└── tests/
    ├── integration/
    └── unit/

frontend/src/
├── app/
│   ├── layout.tsx             # Root layout (Inter font, dark theme)
│   └── page.tsx               # Main page: composes all panels
├── components/
│   ├── controls/              # ConversationPanel, FrameScrubber, PresetSelector
│   ├── dashboard/             # DataFreshnessPanel, EvidencePanel, MetricPanel, GroupImpactPanel, PipelineFlow
│   ├── map/                   # DrawingToolbar, MapControlsHUD, MapLegend, MapViewport
│   └── shared/                # LoadingOverlay
├── hooks/                     # useKeyboardShortcuts, useWebSocket
├── lib/                       # colorScale, mapConfig, ws (WebSocketClient)
├── store/                     # simulationStore (single Zustand store)
└── types/                     # simulation.ts (all TypeScript interfaces)
```

## Data Flow

```
User types scenario
    │
    ▼
ConversationPanel ──▶ useWebSocket.startSimulation()
    │
    ▼
WebSocketClient.connect() ──▶ sends START message
    │
    ▼
Backend WS handler orchestrates:
    │
    ├─ 1. IntentRouter (regex → spaCy) ──▶ ParsedScenario
    │
    ├─ 2. RAG: build_evidence_pack() ──▶ EvidencePack
    │      extract_coefficient_adjustments() ──▶ coefficient_factors
    │
    ├─ 3. Realtime: get_latest_snapshot() ──▶ SnapshotData
    │      overlay.generate_overlay() ──▶ per-cell multipliers
    │
    ├─ 4. GridFactory.initialize() ──▶ GridState
    │      (with overlay applied, confidence arrays set)
    │
    ├─ 5. runner.run_simulation() loop:
    │      primary_loop.step()   ──▶ K, E, confidence_K
    │      secondary_loop.step() ──▶ R, T, H, M, cascading confidence
    │      serializer.to_frame() ──▶ JSON frame
    │
    ├─ 6. tertiary_loop.synthesize_evidence():
    │      translator ──▶ TranslationResult
    │      explainability ──▶ driver breakdowns
    │
    └─ 7. DB: save_simulation()
```

## WebSocket Message Sequence

```
Client                          Server
  │                               │
  │──── START {scenario} ────────▶│
  │                               │
  │◀──── STAGE {parsing} ─────────│
  │◀──── PARSED {params, boundary, snapshot} ──│
  │                               │
  │◀──── STAGE {predicting} ──────│
  │◀──── PREDICTION {forecast} ───│
  │                               │
  │◀──── STAGE {simulating} ──────│
  │◀──── FRAME {month 1} ─────────│  (× N months)
  │◀──── FRAME {month 2} ─────────│
  │  ...                          │
  │                               │
  │◀──── STAGE {retrieving} ──────│
  │◀──── CASE_STUDIES {[]} ───────│
  │                               │
  │◀──── STAGE {synthesizing} ────│
  │◀──── EVIDENCE {report} ───────│
  │◀──── GROUP_SCORES {groups} ───│
  │                               │
  │◀──── DONE {simulation_id} ───│
```

## Simulation Engine

Three loops run per simulation month:

1. **Primary Loop** — Capital and employment shocks
   - `ΔK = K × monthly_rate × sector_weight`
   - Policy boosts (Digital India, Make in India, SEZ, public works)
   - Employment derived from capital changes
   - Confidence decays ×0.97/month

2. **Secondary Loop** — Cascading effects
   - Real estate: neighbor spillover with distance decay
   - Transit congestion from economic activity
   - Housing affordability from real estate + employment
   - Migration pressure from housing + employment
   - Monsoon effects on flood risk
   - Confidence decays ×0.95/month

3. **Tertiary Loop** — Evidence synthesis (post-simulation)
   - Plain-language translation with ₹ amounts
   - Driver breakdown per metric
   - Explainability with top drivers and origins

## Confidence System

Seven data origin levels with associated confidence:

| Origin | Score | Description |
|--------|-------|-------------|
| REAL | 0.85 | Measured from live APIs |
| REAL_TIME_CONTEXT | 0.70 | City-level news signals |
| RAG_EVIDENCE | 0.65 | Historical case study support |
| ESTIMATED | 0.60 | City YAML baselines |
| HARDCODED | 0.40 | Manual constants |
| SYNTHETIC | 0.35 | Distance-decay formulas |
| FALLBACK | 0.25 | Demo/default data |

Confidence propagates through all three loops with per-step decay and is exposed at cell, metric, and aggregate levels.

MetroPulse does not claim prediction certainty. Outputs are scenario estimates for exploration.

## Security Measures

### Rate Limiting
- **POST `/api/v1/ingest`**: In-memory per-IP rate limiter — max 3 requests per 60 seconds (configurable). Returns HTTP 429 with `retry_after_seconds` in the response body.
- Rate limit state is evicted on expiry; no persistent storage needed.

### WebSocket Connection Limits
- Max concurrent WebSocket connections controlled via `WS_MAX_CONNECTIONS` env var (default: 10).
- Exceeding the limit returns WebSocket close code 1013 (Try Again Later).
- Each WS message capped at 64 KB (`MAX_WS_MESSAGE_BYTES`).

### CORS Policy
- Origins configured via `CORS_ORIGINS` env var (comma-separated URLs).
- In production, wildcard `*` origins trigger a startup warning.
- Allowed methods: `GET`, `POST`, `OPTIONS`. Allowed headers: `Content-Type`, `Authorization`.

### Path Traversal Prevention
- `CityConfig.load()` and `CityConfig.load_geojson()` validate `city_name` with `re.fullmatch(r'[a-zA-Z0-9_]+', city_name)`.
- Zone file paths reject `..` patterns.

### Request Logging
- All non-health-check requests are logged in structured JSON format with: method, path, status code, and response time (ms).
- Health endpoints are excluded from logging to reduce noise.

## Testing Strategy

### Unit Tests (378+)
- Located in `backend/tests/unit/`.
- Cover: grid initialization, primary/secondary/tertiary loops, intent parsing, RAG retrieval, coefficient clamping, confidence scoring, serialization, translation.
- Run with: `cd backend && pytest tests/unit/ -v`

### Integration Tests
- Located in `backend/tests/integration/`.
- Test full pipeline: scenario parse → RAG → simulation → evidence synthesis.
- Run with: `cd backend && pytest tests/integration/ -v`

### Load Tests
- Locust-based load tests in `backend/tests/load/locustfile.py`.
- Run with: `locust -f tests/load/locustfile.py --host http://localhost:8000`

### Frontend Tests (52)
- Jest + React Testing Library component tests.
- Run with: `cd frontend && npm run test`

### Coverage Targets
- Unit tests: ~90% coverage
- Integration: ~75% coverage
- Load tests: basic concurrency validation

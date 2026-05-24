# MetroPulse — Scenario-Driven Simulation Design

**Date:** 2026-05-26
**Status:** Approved
**Supersedes:** Current slider-based toy model

---

## Table of Contents

1. [Core Concept](#1-core-concept)
2. [Architecture Overview](#2-architecture-overview)
3. [Scenario Parser (LLM #1)](#3-scenario-parser-llm-1)
4. [Prediction Generator (LLM #2)](#4-prediction-generator-llm-2)
5. [Simulation Engine](#5-simulation-engine)
6. [Case Study Retrieval](#6-case-study-retrieval)
7. [Evidence Synthesizer (LLM #3)](#7-evidence-synthesizer-llm-3)
8. [Frontend Design](#8-frontend-design)
9. [Data Pipeline](#9-data-pipeline)
10. [API Contracts](#10-api-contracts)
11. [Error Handling](#11-error-handling)
12. [Performance Targets](#12-performance-targets)
13. [Implementation Phases](#13-implementation-phases)

---

## 1. Core Concept

Users describe urban policy scenarios in natural language. The system:

1. **Parses** the scenario into structured simulation parameters
2. **Predicts** what the LLM expects will happen (before simulation)
3. **Simulates** the actual outcomes using a deterministic econometric engine
4. **Retrieves** historical precedents from a curated case study database
5. **Synthesizes** evidence-backed analysis comparing prediction vs reality

The LLM is the input layer and the evidence synthesizer. The math engine is the ground truth between them. Results are deterministic and reproducible given the same inputs.

### What Changed From Previous Design

| Aspect | Old (Slider-Based) | New (Scenario-Driven) |
|--------|-------------------|----------------------|
| Input | 3 FDI sliders + polygon draw | Free-text scenario prompt |
| City | Hardcoded NYC/Manhattan | 12 Indian cities |
| Sectors | 3 generic (tech, mfg, real estate) | 7 India-specific |
| Cell baselines | All identical (E=5000, K=0.5) | Spatially differentiated from real data |
| Case studies | 6 non-Indian, RAG dead code | 12 Indian, pgvector retrieval working |
| Database | Fully mocked | Real Supabase integration |
| LLM role | Generic commentary wrapper | Scenario parsing + prediction + evidence synthesis |
| Output | Charts + generic bullets | Prediction vs Reality table + citations + cases |

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      NEXT.JS FRONTEND                        │
│                                                              │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Chat Input   │  │ City Map │  │ Charts   │  │ Evidence │ │
│  │ (scenario)   │  │ (Deck.gl)│  │ (Tremor) │  │ Panel    │ │
│  └──────┬──────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────┼──────────────────────────────▲─────────────────────┘
          │ WebSocket                    │ WebSocket
          ▼                              │
┌──────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Scenario      │  │ Simulation   │  │ Evidence           │ │
│  │ Parser (LLM)  │→ │ Engine (NumPy)│→ │ Synthesizer (LLM) │ │
│  └──────┬───────┘  └──────────────┘  └────────┬───────────┘ │
│         │                                       │             │
│  ┌──────┴───────┐  ┌──────────────┐  ┌────────┴───────────┐ │
│  │ Prediction    │  │ Case Study   │  │ City Data          │ │
│  │ Generator(LLM)│  │ Retriever    │  │ (pre-computed)     │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
          │                              │
┌─────────┴──────────┐    ┌─────────────┴──────────┐
│  SUPABASE POSTGRES  │    │  VECTOR DB (pgvector)  │
│  Regions, Baselines │    │  Case Studies           │
│  Simulations        │    │  Embeddings Index       │
└─────────────────────┘    └────────────────────────┘
```

### Pipeline Per Simulation

```
User types scenario text
       ↓
① LLM: Scenario Parser (structured extraction)
       → city, sectors, FDI deltas, policies, timeframe, keywords
       ↓
② LLM: Prediction Generator
       → "I expect X, Y, Z based on city context + scenario"
       ↓
③ Math Engine: 5-loop econometric cascade
       → spatial_init → primary → secondary → climate → policy
       → monthly frames + aggregate metrics
       ↓
④ Case Study Retrieval (pgvector)
       → ranked historical precedents from curated DB
       ↓
⑤ LLM: Evidence Synthesizer
       → compares prediction vs simulation
       → cites cases + academic sources
       → flags divergences and counter-intuitive outcomes
       ↓
Rendered: prediction box | sim results | divergence | evidence
```

**3 LLM calls per simulation** (parser is fast/cheap, predictor and synthesizer are reasoning models).

---

## 3. Scenario Parser (LLM #1)

Converts free-text scenario into structured simulation parameters.

### Input

User's free-text scenario, e.g.:
> "What happens to Hyderabad if pharma FDI drops 40% due to new US FDA regulations, but the government pushes Smart City Mission simultaneously?"

### Output Schema

```python
class ParsedScenario(BaseModel):
    city: str                          # Matched to available city
    sector_deltas: dict[str, int]      # Sector name → -100 to +100
    policies_active: list[str]         # Active policy names
    public_works_zone: dict | None     # GeoJSON if specified
    horizon_months: int                # 6|12|24|60
    causal_chain: str                  # User's stated reasoning
    keywords: list[str]                # For case study retrieval
```

### Prompt Template

```
You are a scenario parser for an Indian urban simulation system.

Given a user's scenario description, extract structured parameters.

Available cities: Bengaluru, Mumbai, Delhi NCR, Chennai, Hyderabad,
Pune, Kolkata, Ahmedabad, Jaipur, Lucknow, Chandigarh, Bhubaneswar

Available sectors: IT/ITES, Manufacturing, Real Estate, Trade,
Transport/Logistics, Informal Economy, Public Administration

Available policies: SEZ Notification, Smart City Mission, AMRUT,
RERA Compliance, PM Awas Yojana, Make in India, Digital India

User scenario:
{{ user_text }}

Extract as JSON with keys: city, sector_deltas, policies_active,
public_works_zone (null if not specified), horizon_months (default 24
if not stated), causal_chain (user's reasoning in 1-2 sentences),
keywords (for case study search).
```

### Validation Rules

- `city` must match an available city (fuzzy: "Bangalore" → "Bengaluru", "NCR" → "Delhi NCR")
- If city not recognized, return error asking user to clarify
- If all `sector_deltas` are 0 and no `policies_active`, ask user what they want to simulate
- `horizon_months` defaults to 24 if not specified
- `keywords` always includes city name + sector names + policy names

---

## 4. Prediction Generator (LLM #2)

Generates what the LLM expects will happen before the simulation runs.

### Input

- Structured params from parser
- City context profile (pre-built per city)

### City Context Profile

```python
class CityProfile(BaseModel):
    city: str
    state: str
    population: int
    key_sectors: list[str]              # Ordered by economic importance
    gdp_estimate_crores: int
    known_challenges: list[str]         # e.g., ["water stress", "traffic"]
    special_zones: list[str]            # e.g., ["Genome Valley SEZ", "HITEC City"]
    recent_events: list[str]            # e.g., ["Metro Phase 2 completion 2025"]
    sector_weights: dict[str, float]    # Sector → weight in city economy
    spatial_notes: str                  # Free-text about urban form
```

### Output Schema

```python
class Prediction(BaseModel):
    employment_impact: dict             # Per sector: direction + magnitude + confidence
    real_estate_impact: dict            # Zones affected + direction + confidence
    transit_impact: dict                # Direction + affected corridors + confidence
    most_affected_areas: list[str]      # Geographic descriptions
    counter_intuitive: list[str]        # Things that might surprise us
    overall_confidence: str             # "high" | "medium" | "low"
    reasoning: str                      # Full reasoning chain
```

### Prompt Template

```
You are an urban economist specializing in Indian cities.

City context:
{{ city_profile_json }}

Scenario:
{{ causal_chain }}
Sector changes: {{ sector_deltas }}
Active policies: {{ policies_active }}
Timeframe: {{ horizon_months }} months

Based on your knowledge of this city's economy, geography, and
historical patterns, predict:

1. Which areas of the city will be most affected and why
2. Employment impact (direction and rough magnitude per sector)
3. Real estate effects (which zones, direction)
4. Transit/infrastructure implications
5. Your confidence level (high/medium/low) for each prediction
6. What might surprise us (counter-intuitive outcomes)

Output as structured JSON.
```

### Key Decisions

- Prediction is grounded in city context data, not just general LLM knowledge
- Confidence levels create natural comparison metrics: "You predicted X with high confidence, but simulation shows Y"
- Counter-intuitive predictions are explicitly solicited — these are the most valuable divergences

---

## 5. Simulation Engine

Deterministic, fast, reproducible mathematical core.

### 5.1 Spatial Initialization (`spatial_init.py`)

**Replaces:** Current `grid.py` which fills every cell with identical values.

Each H3 cell gets unique baselines computed from real spatial relationships:

```
For each cell c:
  d_cbd   = haversine(c, city_center)
  d_road  = haversine(c, nearest_major_road)
  d_rail  = haversine(c, nearest_rail_station)
  d_coast = haversine(c, coastline)           # if port city

  E_formal(c, 0)   = E_max × exp(-d_cbd / λ_cbd) × (1 + φ_road × exp(-d_road / λ_road))
  E_informal(c, 0) = E_informal_base × (1 - exp(-d_cbd / λ_informal))
  K(c, 0, s)       = K_sector_base(s) × exp(-d_cbd / λ_k(s))
  R(c, 0)          = R_peak × exp(-d_cbd / λ_r) × (1 - ψ_slum)
  T(c, 0)          = T_base + T_peak × exp(-d_cbd / λ_t)
  H(c, 0)          = income_proxy / rent_proxy
  F(c, 0)          = flood_risk_from_elevation_data
  M(c, 0)          = migration_pressure_from_census
```

Lambda constants are configurable per city type (tech_hub, financial, manufacturing, port, administrative).

### 5.2 Grid State Model

```python
@dataclass
class GridState:
    h3_indices: list[str]
    cell_centers: np.ndarray            # [n_cells, 2] lat/lng

    # Economic state (n_cells,) each
    K: np.ndarray                       # Capital by sector [n_cells, n_sectors]
    E_formal: np.ndarray
    E_informal: np.ndarray
    R: np.ndarray                       # Real estate index
    T: np.ndarray                       # Transit congestion
    H: np.ndarray                       # Housing affordability
    F: np.ndarray                       # Flood risk score
    M: np.ndarray                       # Migration pressure

    # Static attributes (pre-computed)
    baselines: dict
    slum_flag: np.ndarray               # Boolean: informal settlement zone

    # Spatial index (pre-computed per region)
    kd_tree: scipy.spatial.KDTree       # Vectorized neighbor search
    zone_flags: dict[str, np.ndarray]   # SEZ, Smart City, etc. boolean masks
```

### 5.3 India-Specific Sector Model

| Sector | Description | Data Source |
|--------|-------------|-------------|
| IT/ITES | Information Technology / IT-enabled Services | NASSCOM, state IT dept |
| Manufacturing | Auto, electronics, pharma, textiles | ASI (Annual Survey of Industries) |
| Real Estate & Construction | Housing, commercial, infrastructure | RERA, HDFC/NHB indices |
| Trade & Hospitality | Retail, hotels, wholesale | GST returns, tourism data |
| Transport & Logistics | Freight, warehousing, port/airport | MoRTH, port trust data |
| Informal Economy | Street vendors, domestic work, casual labor | NSSO employment surveys |
| Public Administration | Government, municipal services, PSUs | State budget documents |

### 5.4 Simulation Loops

**Loop 1 — Spatial Init** (once at start):
- Distance-weighted baselines from CBD, roads, rail, coast
- Pre-compute KD-tree for neighbor search
- Load zone masks (SEZ, Smart City, etc.)

**Loop 2 — Primary Loop** (per month step):
```
ΔK_sector(c, t) = FDI_rate_sector × sector_weight(c) × K(c, t-1)
ΔE_formal(c, t) = α_sector × ΔK(c, t) × employment_elasticity(c)
ΔE_informal(c, t) = β_informal × ΔE_formal(c, t-1)  # 1-month lag
```
All vectorized NumPy. No Python loops over cells.

**Loop 3 — Secondary Loop** (per month step):
```
Real estate cascade (neighbor distance-weighted)
Multi-modal transit congestion
Slum dynamics (informal settlement growth/decay)
Aggregate metrics: GDP delta, unemployment, real estate, transit
```

**Loop 4 — Climate Loop** (per month step, if monsoon active):
```
FloodRisk(c) = f(elevation, drainage, historical_inundation)
If month in monsoon_season:
  K(c, t) -= K(c, t) × flood_impact × FloodRisk(c)
  T(c, t) += flood_congestion_bonus × FloodRisk(c)
```

**Loop 5 — Policy Loop** (per month step):

> **Note:** Policy effect magnitudes below are initial estimates that require calibration against real outcomes during Phase 5 validation. Values will be adjusted based on historical data fitting.

```
SEZ: sector boost within zone + 2km ring (magnitude calibrated from SEZ India data)
Smart City: public works efficacy multiplier (calibrated from Smart City Mission outcomes)
AMRUT: water/sanitation → quality of life (calibrated from AMRUT progress reports)
RERA: real estate volatility reduction (calibrated from RERA implementation states vs non-RERA)
PMAY: slum upgrade rate increase (calibrated from PMAY beneficiary data)
Make in India: manufacturing FDI attraction (calibrated from DPIIT sectoral FDI inflows)
Digital India: IT/ITES FDI attraction (calibrated from NASSCOM reports)
```

### 5.5 Performance Target

- 24-month sim for Mumbai (~1400 cells): ≤ 800ms
- 24-month sim for Delhi NCR (~3500 cells): ≤ 1500ms
- All operations vectorized with NumPy/SciPy
- KD-tree for neighbor search (not nested loops)
- `orjson` for frame serialization (3-5x faster than stdlib)

---

## 6. Case Study Retrieval

pgvector similarity search against curated database of Indian urban precedents.

### Database Schema

```sql
CREATE TABLE case_studies (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  city        TEXT NOT NULL,
  year        INTEGER,
  description TEXT NOT NULL,
  outcome     TEXT NOT NULL,        -- What actually happened
  source      TEXT NOT NULL,        -- Full citation
  source_type TEXT NOT NULL,        -- "academic" | "government" | "industry"
  tags        TEXT[],
  sectors     TEXT[],
  policies    TEXT[],
  embedding   vector(1536),
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON case_studies USING ivfflat
  (embedding vector_cosine_ops) WITH (lists = 100);
```

### Retrieval Flow

1. Combine parser `keywords` + `city` + `sectors` into query string
2. Embed with text-embedding-3-small
3. pgvector cosine similarity search, top 5
4. Boost score if city matches
5. Return with full citation info

### Seed Data (12 Case Studies)

| Title | City | Year | Source Type |
|-------|------|------|-------------|
| Bengaluru IT Boom & Infrastructure Crisis | Bengaluru | 2023 | Academic |
| Mumbai Mill Land to Real Estate Transformation | Mumbai | 2018 | Government |
| Delhi Metro Phase I-IV Impact on Property Values | Delhi NCR | 2024 | Academic |
| Hyderabad Pharma Hub: SEZ Impact | Hyderabad | 2022 | Government |
| Pune Auto Sector FDI & Employment | Pune | 2020 | Industry |
| Ahmedabad GIFT City: Greenfield Finance Hub | Gandhinagar | 2024 | Government |
| Chennai Port-Led Industrial Corridor Growth | Chennai | 2023 | Government |
| Lucknow Administrative Growth & Services | Lucknow | 2022 | Government |
| Bhubaneswar Smart City Mission Outcomes | Bhubaneswar | 2023 | Government |
| Kochi Metro TOD & Real Estate Premium | Kochi | 2023 | Academic |
| Surat Textile Crisis & Diamond Reorientation | Surat | 2021 | Industry |
| Kolkata Urban Decay & Revitalization Efforts | Kolkata | 2022 | Academic |

---

## 7. Evidence Synthesizer (LLM #3)

The final and most valuable LLM call — compares prediction vs reality with evidence.

### Input

- Structured params from parser
- Prediction from generator
- Simulation results (final aggregate metrics + per-cell deltas)
- Retrieved case studies with citations
- City context profile

### Output Structure

```markdown
## Simulation Results

[2-3 sentence summary of what happened]

### Prediction vs Reality

| What We Expected | What Happened | Verdict |
|---|---|---|
| IT employment drops 15% | IT employment drops 22% | Worse than expected |
| Real estate rises in CBD | Real estate rises in CBD | Confirmed |
| Transit worsens in east | Transit improves | Surprise |

### Key Findings

1. **[Finding with spatial reference]**
   Supporting evidence from simulation + citation.

2. **[Finding with temporal pattern]**
   When effects peak, when recovery begins.

3. **[Counter-intuitive outcome]**
   Why this happened, what it means.

### Historical Precedents

- **[Case study title] ([year])**: [outcome summary].
  Source: [citation].

### Sources

- [Academic citation]
- [Government report citation]

### Policy Recommendation

Based on the simulation, one adjustment would significantly
improve outcomes: [specific recommendation with reasoning].
```

### Prompt Template

```
You are an urban economics analyst synthesizing simulation results.

## Scenario
{{ parsed_params }}

## Prediction (made before simulation)
{{ prediction_json }}

## Simulation Results
{{ final_metrics_json }}
{{ cell_delta_summary }}

## Historical Precedents Retrieved
{{ case_studies_text }}

## City Context
{{ city_profile }}

---

Compare the prediction against simulation results. For each prediction,
mark it as "Confirmed", "Partially Confirmed", "Wrong", or "Surprise".

Then provide 3-5 key findings with supporting evidence from:
1. The simulation data (cite specific metrics and spatial patterns)
2. The historical precedents (cite by title and year)
3. Academic/government sources from the case studies

Highlight any counter-intuitive outcomes where the simulation
diverges from naive expectations.

End with one concrete policy recommendation grounded in the data.
```

### Key Design Decisions

- The "Prediction vs Reality" table is the signature output
- Evidence is grounded in retrieved case studies (not hallucinated)
- Academic citations come from the case study DB source field
- Policy recommendation is constrained to what the simulation actually modeled
- If no case studies are found, the synthesizer notes the absence and relies on simulation data alone

---

## 8. Frontend Design

### 8.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ┌─ Chat Input ────────────────────────────────────────────┐ │
│ │ What happens to Hyderabad if pharma FDI drops 40%...    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Map (60%) ───────────┐ ┌─ Evidence Panel (40%) ───────┐ │
│ │                        │ │                               │ │
│ │   [Deck.gl H3 hex      │ │ ## Prediction vs Reality     │ │
│ │    grid over city]      │ │ | Expected | Actual | Verdict│ │
│ │                        │ │                               │ │
│ │                        │ │ ## Key Findings              │ │
│ │                        │ │ 1. Employment drops 18%...   │ │
│ │                        │ │                               │ │
│ │                        │ │ ## Historical Precedents     │ │
│ │                        │ │ - Vizag SEZ (2019)...        │ │
│ │                        │ │                               │ │
│ └────────────────────────┘ └───────────────────────────────┘ │
│                                                             │
│ ┌─ Dashboard (collapsible) ────────────────────────────────┐ │
│ │ [GDP]  [Unemployment]  [RE Index]  [Transit]  [Charts]  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Chat Input Component

- Single-line input that expands on focus
- Enter to submit, Shift+Enter for newline
- Shows parsed params as a collapsible summary after submission
- Processing states: "Parsing scenario..." → "Generating prediction..." → "Running simulation..." → "Synthesizing evidence..."
- Each state is a progress step shown to the user

### 8.3 Evidence Panel Component

- Replaces the current AIInsightPanel
- Renders structured markdown from the synthesizer
- "Prediction vs Reality" table with color-coded verdicts:
  - Confirmed: green
  - Partially Confirmed: yellow
  - Wrong: red
  - Surprise: blue
- Case studies are expandable cards with full citations
- Sources section with proper academic formatting

### 8.4 Map Viewport Updates

- Default view centers on selected Indian city
- Map style: CartoDB Dark Matter (global, no API key needed)
- Indian city coordinates pre-configured
- Overlays: SEZ boundaries, slum zones, flood risk heatmap
- Drawing tool still available for public works zone specification

### 8.5 State Management Updates

```typescript
interface SimulationState {
  // Input
  scenarioText: string;
  parsedScenario: ParsedScenario | null;

  // Prediction
  prediction: Prediction | null;

  // Simulation
  frames: SimulationFrame[];
  currentFrame: SimulationFrame | null;
  metrics: AggregateMetrics | null;

  // Evidence
  evidence: EvidenceReport | null;
  caseStudies: CaseStudy[];

  // Pipeline status
  pipelineStage: 'idle' | 'parsing' | 'predicting' | 'simulating' |
                 'retrieving' | 'synthesizing' | 'done' | 'error';
  error: string | null;
}
```

---

## 9. Data Pipeline

### 9.1 City Targets (12 Cities)

| City | Type | H3 Cells (res 8) | Priority |
|------|------|-------------------|----------|
| Bengaluru | IT hub, startup capital | ~1800 | P0 |
| Mumbai | Financial + port | ~1400 | P0 |
| Delhi NCR | Capital region, manufacturing | ~3500 | P0 |
| Chennai | Auto + IT + port | ~1200 | P0 |
| Hyderabad | Pharma + IT | ~1000 | P0 |
| Pune | Auto + IT + education | ~900 | P0 |
| Kolkata | Port + services | ~1100 | P0 |
| Ahmedabad | Textiles + pharma + auto | ~700 | P0 |
| Jaipur | Tourism + handicrafts | ~500 | P1 |
| Lucknow | Administrative + services | ~600 | P1 |
| Chandigarh tricity | Planned city, services | ~300 | P1 |
| Bhubaneswar | IT + admin + education | ~300 | P1 |

### 9.2 Data Access Notes

> **Important:** Not all data sources are freely downloadable. Access tiers:
> - **Freely available:** OSM road network, NASA VIIRS night lights, Census 2011 (bulk download), SEZ India boundaries, IMD rainfall data
> - **Requires registration:** ISRO Bhuvan portal (free but institutional email), NHB RESIDEX (request-based)
> - **Requires institutional access:** NSSO PLFS microdata (through NSSO data portal), ASI unit-level data (through MOSPI), NASSCOM reports (membership)
> - **Requires scraping/API:** RERA filings (state-specific portals), GST returns (aggregated only via CBIC)
>
> **Fallback strategy:** Where real data is unavailable, use proxy data (night lights for economic activity, OSM for infrastructure density) and note the approximation in city configs. The system must work with imperfect data and improve as better data becomes available.

| Data | Source | Format | Script |
|------|--------|--------|--------|
| City boundaries | Survey of India / Bhuvan | GeoJSON | `scripts/seed_cities.py` |
| Land use/land cover | ISRO Bhuvan (30m) | GeoTIFF → H3 | `scripts/preprocess/lulc_to_h3.py` |
| Road network | OpenStreetMap India | .osm.pbf → proximity | `scripts/preprocess/road_proximity.py` |
| Rail/metro stations | Indian Railways, MoHUA | Point GeoJSON | `scripts/preprocess/transit_nodes.py` |
| Population density | Census 2011 (ward-level) | Ward → H3 | `scripts/preprocess/census_to_h3.py` |
| Night lights | NASA VIIRS / ISRO | GeoTIFF → baseline | `scripts/preprocess/nl_to_baseline.py` |
| FDI data | DPIIT, RBI | CSV | `data/fdi_india.csv` |
| Employment | NSSO PLFS, ASI | District tables | `data/employment_baselines.py` |
| Real estate | NHB RESIDEX, RERA | Index by city | `data/realestate_indices.py` |
| SEZ boundaries | SEZ India, Ministry of Commerce | KML/GeoJSON | `scripts/preprocess/sez_zones.py` |
| Monsoon/flood | IMD, NDMA | Gridded data | `scripts/preprocess/flood_risk.py` |
| Slum locations | Ministry of Housing | Polygon GeoJSON | `scripts/preprocess/slum_boundaries.py` |

### 9.3 City Configuration Files

Each city gets a YAML config in `data/cities/`:

```yaml
name: Hyderabad
state: Telangana
country: India
center: [17.3850, 78.4867]
zoom: 11
boundary_source: "hyderabad_boundary.geojson"
population: 10000000
city_type: "pharma_it_hub"
port_city: false
monsoon_season: [6, 7, 8, 9]
metro_system: true

baselines:
  employment_formal: 2800000
  employment_informal: 4200000
  gdp_estimate_crores: 175000
  slum_population_pct: 0.12

sector_weights:
  it_ites: 0.30
  manufacturing: 0.25    # Pharma dominated
  real_estate: 0.15
  trade_hospitality: 0.12
  transport_logistics: 0.08
  informal: 0.06
  public_admin: 0.04

constants:
  alpha_default: 0.55
  beta_informal: 0.4
  gamma_realestate: 0.12
  delta_congestion: 0.10
  lambda_cbd_employment: 4.5
  lambda_road_boost: 1.5
  flood_impact: 0.15

special_zones:
  - type: "sez"
    name: "Genome Valley"
    file: "data/sez/genome_valley.geojson"
    sectors: ["manufacturing"]  # Pharma
    boost: 0.25
  - type: "sez"
    name: "HITEC City"
    file: "data/sez/hitec_city.geojson"
    sectors: ["it_ites"]
    boost: 0.20
```

---

## 10. API Contracts

### 10.1 WebSocket: Run Simulation

**Endpoint:** `wss://<host>/ws/simulate`

**Client → Server:**
```json
{
  "type": "START",
  "scenario": "What happens to Hyderabad if pharma FDI drops 40%..."
}
```

**Server → Client (pipeline messages):**

```json
{"type": "STAGE", "stage": "parsing", "message": "Analyzing scenario..."}

{"type": "PARSED", "params": { ... }}

{"type": "STAGE", "stage": "predicting", "message": "Generating prediction..."}

{"type": "PREDICTION", "prediction": { ... }}

{"type": "STAGE", "stage": "simulating", "message": "Running simulation..."}

{"type": "FRAME", "payload": { "month": 1, "cells": [...], "metrics": {...} }}

{"type": "FRAME", "payload": { "month": 2, ... }}

...

{"type": "STAGE", "stage": "retrieving", "message": "Finding historical precedents..."}

{"type": "CASE_STUDIES", "studies": [...]}

{"type": "STAGE", "stage": "synthesizing", "message": "Synthesizing evidence..."}

{"type": "EVIDENCE", "markdown": "## Simulation Results\n..."}

{"type": "DONE", "simulationId": "uuid"}
```

### 10.2 REST: Regions

```
GET /api/regions
GET /api/regions/{id}/baseline
GET /api/regions/{id}/profile
```

### 10.3 REST: Case Studies

```
GET /api/case-studies
GET /api/case-studies?city=Hyderabad&sector=manufacturing
```

### 10.4 REST: Simulations

```
GET /api/simulations            # List past runs
GET /api/simulations/{id}       # Full result
```

### 10.5 Response Envelope

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "requestId": "uuid", "latencyMs": 42 }
}
```

---

## 11. Error Handling

### Pipeline Errors

| Stage | Error | Behavior |
|-------|-------|----------|
| Parsing | City not recognized | Send ERROR message: "I couldn't identify the city. Did you mean Bengaluru?" |
| Parsing | All deltas zero, no policies | Send ERROR: "Please specify what changes you want to simulate." |
| Parsing | LLM timeout (> 10s) | Send ERROR: "Failed to parse scenario. Please try again." |
| Prediction | LLM timeout (> 15s) | Skip prediction, proceed with simulation. Note: "Prediction unavailable." |
| Simulation | Exceeds 3s deadline | Terminate, send ERROR, do not save. |
| Simulation | NaN in cell state | Replace with 0.0, log warning. |
| Retrieval | pgvector returns 0 results | Proceed without precedents. Note in evidence: "No historical precedents found." |
| Synthesis | LLM timeout (> 15s) | Send raw simulation metrics + case studies as fallback. |
| Synthesis | LLM returns malformed output | Send raw metrics + case study summaries. |

### Client Errors

| Scenario | Behavior |
|----------|----------|
| WS disconnect mid-stream | Reconnect with exponential backoff. Resume from last stage. |
| Map tile load failure | Fallback to OpenStreetMap raster tiles. |

---

## 12. Performance Targets

| Metric | Target |
|--------|--------|
| Scenario parsing (LLM #1) | ≤ 3s |
| Prediction generation (LLM #2) | ≤ 5s |
| Simulation: 24-month, Mumbai (~1400 cells) | ≤ 800ms |
| Simulation: 24-month, Delhi NCR (~3500 cells) | ≤ 1500ms |
| Case study retrieval (pgvector) | ≤ 200ms |
| Evidence synthesis (LLM #3) | ≤ 10s |
| Total pipeline (user click → evidence shown) | ≤ 20s |
| REST API latency (p95) | ≤ 200ms |
| UI frame rate (3D map) | ≥ 45 FPS |
| Max concurrent simulations | 10 |

---

## 13. Implementation Phases

### Phase 0: Data Pipeline (2 weeks)
- City boundary GeoJSONs for 12 cities
- City config YAML files
- Preprocessing scripts (LULC, census, night lights, SEZ, slum, flood)
- FDI + employment baseline data compilation
- 12 Indian case studies with embeddings

### Phase 1: Engine Rewrite (2 weeks)
- Spatial initialization module
- 7-sector GridState with new dimensions
- Rewrite primary loop (vectorized, multi-sector)
- Rewrite secondary loop (slum dynamics, multi-modal transit)
- New climate loop
- New policy loop
- Rewrite runner (5-loop orchestration, deadline check)
- Rewrite serializer (orjson, compressed frames)

### Phase 2: Database & API (1 week)
- Real Supabase integration (remove mock)
- Region CRUD from DB
- City profiles endpoint
- Case study CRUD + search
- Multi-region WebSocket handler with pipeline stages
- Scenario parser integration
- Prediction generator integration
- Evidence synthesizer integration

### Phase 3: Frontend Overhaul (1.5 weeks)
- Chat input component
- Pipeline progress indicator
- Prediction vs Reality display
- Evidence panel (replaces AIInsightPanel)
- City selector (auto-detected from scenario, manual override available)
- Map defaults for Indian cities
- New overlays (SEZ, slum, flood risk, transit)
- Remove FDI sliders (replaced by chat input)
- Update state management for pipeline stages

### Phase 4: Polish & Performance (1 week)
- Benchmark simulation per city
- Numba JIT for hot loops if needed
- WebSocket compression (permessage-deflate)
- Indian map style
- Error handling for all pipeline stages
- Loading states for each pipeline stage

### Phase 5: Testing & Validation (1 week)
- Unit tests: spatial_init, climate, policy loops
- Integration tests: full pipeline (parse → predict → simulate → retrieve → synthesize)
- Validation tests: compare output vs real Indian data
- 12-city load test
- E2E: frontend scenario workflow

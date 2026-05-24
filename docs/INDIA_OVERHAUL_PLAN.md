# MetroPulse — India-Focused Overhaul Plan

**Date:** 2026-05-25  
**Scope:** Complete simulation engine rewrite + India data pipeline  
**Status:** Proposed

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Root Cause Analysis](#2-root-cause-analysis)
3. [Simulation Engine Redesign](#3-simulation-engine-redesign)
4. [India Data Pipeline](#4-india-data-pipeline)
5. [New Feature Catalog](#5-new-feature-catalog)
6. [Frontend Overhaul](#6-frontend-overhaul)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Success Metrics](#8-success-metrics)

---

## 1. Executive Summary

The current simulation is a **toy model dressed as a digital twin**. Core issues:

| Problem | Severity | Why It Matters |
|---------|----------|----------------|
| NYC-only geometry & data | **Critical** | The entire codebase is hardcoded for Manhattan. No Indian city exists. |
| Uniform cell baselines | **Critical** | Every H3 cell starts identical (E=5000, K=0.5). No spatial differentiation. |
| Three generic sectors | **High** | India's urban economy is driven by IT/ITES, pharma, auto, textiles, informal trade — none modeled. |
| Guessed constants | **High** | α, β, γ, δ have no empirical backing from Indian economic data. |
| O(n²) neighbor search | **Medium** | `get_neighbor_distances()` is unacceptably slow for large Indian metro grids. |
| No informal economy | **High** | 80%+ of Indian urban employment is informal — completely absent. |
| No disaster/climate | **Medium** | Monsoon flooding shapes every Indian city's trajectory. |
| No migration | **Medium** | Rural-to-urban migration is the primary growth driver in Indian cities. |
| Non-Indian case studies | **High** | 6 case studies, all from US/Europe/China. Zero Indian precedent. |

**This plan overhauls MetroPulse into a credible India-focused urban simulation platform.**

---

## 2. Root Cause Analysis

### 2.1 Simulation Engine (backend/engine/)

| File | Issue | Impact |
|------|-------|--------|
| `grid.py` | `GridState.initialize()` fills every cell with identical values | No spatial heterogeneity → all cells react identically to FDI shock |
| `grid.py` | `get_neighbor_distances()` loops every cell against every cell checking `jdx in neighbors()` | O(n·k) where k = avg neighbors scanned × n. For Mumbai (~2000 cells at res 8), this creates ~14M checks |
| `primary_loop.py` | 3 hardcoded sectors with fixed weights 0.4/0.35/0.25 | Cannot model India-specific sectors like IT/ITES, pharma, auto |
| `primary_loop.py` | Public works boost computes haversine in a Python loop | Not vectorized; dominates runtime for large grids |
| `secondary_loop.py` | Real estate cascade uses neighbor pairs with exp(-d/λ_R) weighting | Doesn't account for Indian land value gradients (CBD spikes, slum flatness) |
| `secondary_loop.py` | Transit congestion = δ × ΔE / capacity, with uniform capacity=1 | Ignores Indian transit reality (overloaded buses, shared autos, metro) |
| `runner.py` | `db.batch_save()` catches all exceptions silently | Failures are invisible |
| `tertiary_loop.py` | `db.search_case_studies([0.0]*1536)` passes zero vector | Always returns no results — RAG pipeline is dead code |
| `tertiary_loop.py` | All 6 case studies are non-Indian | Irrelevant precedent for India policy analysis |

### 2.2 Database Layer (backend/app/db.py)

| Issue | Impact |
|-------|--------|
| `list_regions()` returns hardcoded NYC regions | No Indian cities available |
| `get_baseline()` returns constant values | No real baseline data |
| `search_case_studies()` always returns empty list | RAG pipeline non-functional |
| `save_simulation()` generates random UUID but never writes | Persistence is fake |

### 2.3 Frontend

| Issue | Impact |
|-------|--------|
| `mapConfig.ts`: NYC coordinates, US Mapbox style | Wrong geography, wrong aesthetics for India |
| No Indian city region boundaries | User can only select NYC area |
| FDI as only policy lever | No Indian-specific policies (SEZ notification, Smart City Mission, AMRUT) |
| Map style uses CartoDB dark-matter | Needs Indian context (water bodies, district boundaries, ward boundaries) |

---

## 3. Simulation Engine Redesign

### 3.1 India-Specific Sector Model

Replace the 3 generic sectors with a **7-sector India-urban model**:

| Sector | Weight | Description | Data Source |
|--------|--------|-------------|-------------|
| IT/ITES | 0.25 | Information Technology / IT-enabled Services | NASSCOM, state IT dept reports |
| Manufacturing | 0.20 | Automotive, electronics, pharma, textiles | ASI (Annual Survey of Industries) |
| Real Estate & Construction | 0.15 | Housing, commercial real estate, infrastructure | RERA data, HDFC/NHB indices |
| Trade & Hospitality | 0.12 | Retail, hotels, restaurants, wholesale | GST returns, tourism data |
| Transport & Logistics | 0.10 | Freight, warehousing, port/airport activity | MoRTH, port trust data |
| Informal Economy | 0.10 | Street vendors, domestic work, casual labor | NSSO employment surveys |
| Public Administration | 0.08 | Government, municipal services, PSUs | State budget documents |

**Implementation**: `backend/engine/primary_loop.py` — replace `SECTOR_WEIGHTS` dict with this expanded set.

### 3.2 Spatial Heterogeneity Engine

Current: every cell starts with E=5000, K=0.5, R=1.0, T=0.3

New design — **distance-weighted initialization from real urban form**:

```
For each cell c:
  d_cbd = haversine_distance(c, city_center)          # km from CBD
  d_road = haversine_distance(c, nearest_major_road)   # km from arterial
  d_rail = haversine_distance(c, nearest_rail_station) # km from station
  d_coast = haversine_distance(c, coastline)           # km from coast (if port city)

  E(c, 0) = E_max × exp(-d_cbd / λ_cbd) × (1 + φ_road × exp(-d_road / λ_road))
  K(c, 0) = K_cbd × exp(-d_cbd / λ_k) + K_informal_base
  R(c, 0) = R_peak × exp(-d_cbd / λ_r) × (1 - ψ_slum)
  T(c, 0) = T_base + T_peak × exp(-d_cbd / λ_t)
```

Where `ψ_slum` flags informal settlement zones (from ward-level government data).

**New file**: `backend/engine/spatial_init.py` with configurable λ constants per city type.

### 3.3 India-Specific Simulation Loops

#### 3.3.1 Primary Loop — Extended (8 dimensions)

```
ΔK_sector(c, t) = FDI_rate_sector × sector_weight(c) × K(c, t-1)
ΔE_formal(c, t) = α_sector × ΔK(c, t) × employment_elasticity(c)
ΔE_informal(c, t) = β_informal × ΔE_formal(c, t-1)    # Informal follows formal with 1-month lag
                                                       # Migration: +η × (wage_gap / distance_from_rural)
```

#### 3.3.2 Secondary Loop — India Enhancements

**Real Estate with Slum Dynamics:**
```
ΔR(c, t) = γ × Σ_neighbors [ΔK × exp(-d / λ_R)] - slum_decay
slum_decay = slum_upgrade_rate × (1 - R(c)) if zone active
If R(c) < slum_threshold → mark cell as "at risk" for informal settlement growth
```

**Transit with Indian Multi-Modal Congestion:**
```
ΔT(c, t) = δ × ΔE(c, t) / capacity(c)
capacity(c) = capacity_road(c) + capacity_rail(c) + capacity_metro(c)
Congestion effect of informal transit (auto-rickshaws, shared vans) modeled as
  smoothing factor on capacity
```

#### 3.3.3 Tertiary Loop — Monsoon & Climate

**New file**: `backend/engine/climate_loop.py`

```
FloodRisk(c) = elevation_inverse(c) × drainage_proximity(c) × historical_inundation(c)
If month in monsoon_season[city]:
  K(c, t) -= K(c, t) × flood_impact × floodRisk(c)
  T(c, t) += flood_congestion_bonus × floodRisk(c)
```

#### 3.3.4 Policy Loop — Indian Government Schemes

**New file**: `backend/engine/policy_loop.py`

Model the effect of:
- **SEZ notification**: boost to manufacturing & IT K within zone + 2km ring
- **Smart City Mission**: public works multiplier + data infrastructure boost
- **AMRUT**: water/sanitation infrastructure improvement → quality-of-life → population retention
- **RERA**: real estate transparency → reduced speculative bubble risk
- **PM Awas Yojana**: affordable housing → slum upgrade rate increase
- **GST implementation**: formalization incentive → informal→formal migration rate

### 3.4 Performance: Vectorized Grid Operations

| Current | Problem | Fix |
|---------|---------|-----|
| `get_neighbor_distances()` loops O(n·k) | ~14M iterations for Mumbai | Pre-compute k-d tree once, store per region |
| Public works haversine in Python loop | ~2000 trig calls + arcsin per step | NumPy vectorized: `d = 6371 * 2 * arcsin(sqrt(hav))` |
| Single-threaded | Only uses 1 core | Use `numba` jit for hot loops OR `scipy.spatial.distance.cdist` |
| Serial frame serialization | JSON serial of 2000 cells each step | Use `orjson` (3-5x faster) for frame serialization |

### 3.5 Grid Spatiotemporal Data Structure

Current: `GridState` holds flat arrays. After enhancement:

```python
@dataclass
class GridState:
    h3_indices: list[str]           # cell identifiers
    cell_centers: np.ndarray        # [n_cells, 2] pre-computed lat/lng
    
    # Core economic state (n_cells,)
    K: np.ndarray                   # Capital allocation by sector [n_cells, n_sectors]
    E_formal: np.ndarray            # Formal employment
    E_informal: np.ndarray          # Informal employment
    R: np.ndarray                   # Real estate index
    T: np.ndarray                   # Transit congestion
    H: np.ndarray                   # Housing affordability index (NEW)
    F: np.ndarray                   # Flood risk score (NEW)
    M: np.ndarray                   # Migration pressure (NEW)
    
    # Static attributes (pre-computed)
    baselines: dict                 # Baseline per metric
    lulc: np.ndarray                # Land use / land cover classification
    elevation: np.ndarray           # Digital elevation model
    slum_flag: np.ndarray           # Bool: informal settlement
    
    # Spatial index (pre-computed per region)
    kd_tree: scipy.spatial.KDTree
    zone_flags: dict[str, np.ndarray]  # SEZ, Smart City, etc. boolean masks
```

---

## 4. India Data Pipeline

### 4.1 City Targets (Phase 1)

| City | Type | H3 Cells (res 8) | Data Priority |
|------|------|-------------------|---------------|
| **Bengaluru** | IT hub, startup capital | ~1800 | **P0** |
| **Mumbai** | Financial + port + bollywood | ~1400 | **P0** |
| **Delhi NCR** | Capital region, manufacturing | ~3500 | **P0** |
| **Pune** | Auto + IT + education | ~900 | P1 |
| **Chennai** | Auto + IT + port | ~1200 | P1 |
| **Hyderabad** | Pharma + IT | ~1000 | P1 |
| **Ahmedabad** | Textiles + pharma + auto | ~700 | P1 |
| **Kolkata** | Port + services + jute | ~1100 | P1 |
| **Lucknow** | Administrative + services | ~600 | P2 |
| **Jaipur** | Tourism + handicrafts | ~500 | P2 |
| **Chandigarh tricity** | Planned city, services | ~300 | P2 |
| **Bhubaneswar** | IT + admin + education | ~300 | P2 |

### 4.2 Data Sources

| Data | Source | Format | Integration |
|------|--------|--------|-------------|
| **City boundaries** | Survey of India / Bhuvan portal | GeoJSON | `scripts/seed_cities.py` |
| **Land use/land cover** | ISRO Bhuvan (30m resolution) | GeoTIFF → H3 aggregation | `preprocess/lulc_to_h3.py` |
| **Road network** | OpenStreetMap India | `.osm.pbf` → distance to nearest road | `preprocess/road_proximity.py` |
| **Rail/metro stations** | Indian Railways, MoHUA | Point GeoJSON | `preprocess/transit_nodes.py` |
| **Population density** | Census 2011 (ward-level) + projected | Ward boundary GeoJSON → H3 | `preprocess/census_to_h3.py` |
| **Night lights** | NASA VIIRS / ISRO | GeoTIFF → economic activity proxy | `preprocess/nl_to_baseline.py` |
| **FDI data** | DPIIT, RBI, state industrial depts | CSV by sector & year | `data/fdi_india.csv` |
| **Employment** | NSSO Periodic Labour Force Survey, ASI | District-level tables | `data/employment_baselines.py` |
| **Real estate** | NHB RESIDEX, RERA filings | Index by city | `data/realestate_indices.py` |
| **SEZ boundaries** | SEZ India, Ministry of Commerce | KML/GeoJSON | `preprocess/sez_zones.py` |
| **Monsoon/flood** | IMD rainfall data, NDMA flood maps | Gridded rainfall + flood plains | `preprocess/flood_risk.py` |
| **Slum locations** | Ministry of Housing, state slum boards | Polygon GeoJSON | `preprocess/slum_boundaries.py` |

### 4.3 Case Studies — India Edition

Replace all 6 existing case studies with India-specific ones:

| Title | City | Year | Relevance |
|-------|------|------|-----------|
| Bengaluru IT Boom & Infrastructure Crisis | Bengaluru | 2023 | Tech FDI + traffic congestion + water crisis |
| Mumbai Mill Land to Real Estate Transformation | Mumbai | 2018 | Deindustrialization → RE boom |
| Delhi Metro Phase I-IV Impact on Property Values | Delhi NCR | 2024 | Transit infrastructure → RE cascade |
| Hyderabad Pharma Hub: SEZ Impact | Hyderabad | 2022 | SEZ → manufacturing + pharma cluster |
| Pune Auto Sector FDI & Employment | Pune | 2020 | Manufacturing FDI + ancillary ecosystem |
| Ahmedabad GIFT City: Greenfield Finance Hub | Gandhinagar | 2024 | Tax policy → new financial district |
| Chennai Port-Led Industrial Corridor Growth | Chennai | 2023 | Port + manufacturing corridor |
| Lucknow Administrative Growth & Services | Lucknow | 2022 | Government services → tertiary sector |
| Bhubaneswar Smart City Mission Outcomes | Bhubaneswar | 2023 | Smart City + IT incubation |
| Kochi Metro TOD & Real Estate Premium | Kochi | 2023 | Transit-oriented development |
| Surat Textile Crisis & Diamond Reorientation | Surat | 2021 | External shock → sector pivot |
| Kolkata Urban Decay & Revitalization Efforts | Kolkata | 2022 | Post-industrial decline → regeneration |

### 4.4 City Configuration Files

Each city gets a **configuration file** (JSON/YAML):

```yaml
# data/cities/bengaluru.yaml
name: Bengaluru
state: Karnataka
country: India
center: [12.9716, 77.5946]
zoom: 11
boundary_source: "bbmp_ward_boundary.geojson"
population: 13000000
city_type: "tech_hub"
port_city: false
monsoon_season: [6, 7, 8, 9]  # June-September
metro_system: true

baselines:
  employment_formal: 3500000
  employment_informal: 5000000
  gdp_estimate_crores: 550000
  slum_population_pct: 0.15

sectors_weights:
  it_ites: 0.35
  manufacturing: 0.12
  real_estate: 0.18
  trade_hospitality: 0.14
  transport_logistics: 0.07
  informal: 0.08
  public_admin: 0.06

constants:
  alpha_default: 0.55      # Lower than US model (80% informal dampening)
  beta_informal: 0.4       # Informal→formal transition rate
  gamma_realestate: 0.12
  delta_congestion: 0.10
  lambda_cbd_employment: 4.5  # km
  lambda_road_boost: 1.5
  flood_impact: 0.15

special_zones:
  - type: "sez"
    name: "Electronic City"
    file: "data/sez/electronic_city.geojson"
    sectors: ["it_ites", "manufacturing"]
    boost: 0.25
  - type: "sez"
    name: "Whitefield IT Corridor"
    file: "data/sez/whitefield.geojson"
    sectors: ["it_ites"]
    boost: 0.20

policies:
  smart_city: true
  mission_name: "Bengaluru Smart City"
  amrut: true
  metro_phase: 3
```

---

## 5. New Feature Catalog

### 5.1 Policy Intervention Layer (New Engine Module)

Users can toggle Indian government schemes as simulation inputs:

| Policy | Type | Implementation |
|--------|------|----------------|
| **SEZ Notification** | Zone-based | Boost to applicable sectors within zone + 2km radius |
| **Smart City Mission** | City toggle | +15% public works efficacy, +10% data infrastructure |
| **AMRUT** | City toggle | Water/sanitation improvement → +5% quality of life |
| **RERA Compliance** | City toggle | Real estate volatility reduction (-20% to speculation) |
| **PM Awas Yojana** | City toggle | Slum upgrade rate × 2 |
| **Make in India** | Sector toggle | +10% manufacturing FDI attraction |
| **Digital India** | Sector toggle | +15% IT/ITES FDI attraction |

**New frontend component**: `PolicyPanel.tsx` with toggle switches + zone selector for SEZ.

### 5.2 Scenario Engine Upgrade

Current presets (Tech Boom, Manufacturing Renaissance, etc.) are generic. Replace with India-specific:

| Scenario | FDI Changes | Policy Toggles | Horizon |
|----------|-------------|----------------|---------|
| **Bengaluru-Style IT Boom** | IT +80%, Others -10% | Digital India ON, SEZ ON | 24m |
| **Gujarat Manufacturing Push** | Manufacturing +60%, IT +10% | Make in India ON, SEZ ON | 60m |
| **Mumbai Infrastructure Overhaul** | RealEstate +30%, Transport +40% | AMRUT ON, Smart City ON, PMAY ON | 24m |
| **Delhi-Mumbai Corridor Opening** | Logistics +50%, Manufacturing +30% | SEZ ON, Make in India ON | 60m |
| **Monsoon Crisis Scenario** | All -15% | Flood mitigation ON | 12m |
| **Post-COVID Recovery** | IT +40%, Hospitality +20% | Digital India ON, RERA ON | 24m |
| **Slum Rehabilitation Push** | RealEstate -10%, Construction +30% | PMAY ON, AMRUT ON | 60m |

### 5.3 New Metrics & Dashboard Charts

| Metric | Source | New? |
|--------|--------|------|
| GDP Delta (existing) | `Σ(K(t) - K(0)) / ΣK(0)` | ❌ |
| Unemployment Rate (existing) | `1 - (ΣE(t)/ΣE(0)) × base_unemp` | ❌ |
| Real Estate Index (existing) | `mean(R)` | ❌ |
| Transit Congestion (existing) | `mean(T)` | ❌ |
| **Informal Employment Share** | `ΣE_informal / (ΣE_formal + ΣE_informal)` | **NEW** |
| **Housing Affordability Index** | `mean(H)` where H = income / rent proxy | **NEW** |
| **Slum Population Estimate** | `count(cells where slum_flag ∧ R < threshold)` | **NEW** |
| **Flood Disruption Score** | `mean(F × K_loss)` | **NEW** |
| **Migration Balance** | `ΣM_in - ΣM_out` | **NEW** |
| **Sector Concentration Index** | Herfindahl-Hirschman on sector K shares | **NEW** |

### 5.4 Map Layer Enhancements

| Layer | Description |
|-------|-------------|
| **Slum overlay** | Red zones where informal settlements exist (from government data) |
| **SEZ boundaries** | Green outlines with sector labels |
| **Flood risk heatmap** | Blue gradient by inundation probability |
| **Metro/rail stations** | Icon overlay with catchment rings |
| **Ward boundaries** | Administrative boundary overlay (upon zoom ≥ 12) |
| **Informal economy hotspots** | Derived from night lights + slum data |

### 5.5 Temporal Features

| Feature | Description |
|---------|-------------|
| **Monsoon season slider** | Tick months 6-9 → auto-enable climate loop |
| **Historical comparison** | Run same params against 2011, 2021, 2026 baselines |
| **Scenario branching** | A/B comparison of two param sets side by side |
| **Animated timeline** | Play/pause simulation with variable speed |

---

## 6. Frontend Overhaul

### 6.1 Map Defaults for India

```typescript
// lib/mapConfig.ts
export const INDIA_CITIES: Record<string, MapViewState> = {
  bengaluru: { longitude: 77.5946, latitude: 12.9716, zoom: 11, pitch: 45, bearing: 0 },
  mumbai:    { longitude: 72.8777, latitude: 19.0760, zoom: 11, pitch: 45, bearing: 0 },
  delhi:     { longitude: 77.2090, latitude: 28.6139, zoom: 10, pitch: 45, bearing: 0 },
  chennai:   { longitude: 80.2707, latitude: 13.0827, zoom: 11, pitch: 45, bearing: 0 },
  hyderabad: { longitude: 78.4867, latitude: 17.3850, zoom: 11, pitch: 45, bearing: 0 },
  pune:      { longitude: 73.8567, latitude: 18.5204, zoom: 11, pitch: 45, bearing: 0 },
  kolkata:   { longitude: 88.3639, latitude: 22.5726, zoom: 11, pitch: 45, bearing: 0 },
  ahmedabad: { longitude: 72.5714, latitude: 23.0225, zoom: 11, pitch: 45, bearing: 0 },
};
```

Map style: Switch to **CartoDB Dark Matter (global)** or **Mapbox India-specific** style with Indian waterbody rendering.

### 6.2 New UI Components

| Component | Description |
|-----------|-------------|
| `PolicyPanel.tsx` | Toggle switches for Indian government schemes |
| `CitySelector.tsx` | Dropdown with city preview (population, GDP, key sectors) |
| `SectorBreakdown.tsx` | Stacked bar chart showing employment by sector (formal vs informal) |
| `MonsoonToggle.tsx` | Checkbox + intensity slider for climate simulation |
| `MigrationSlider.tsx` | Rural→urban migration rate adjustment |
| `A_B_Comparer.tsx` | Side-by-side metric comparison of two simulation runs |
| `MapLegendIndia.tsx` | Extended legend with slum, SEZ, flood layers |

### 6.3 Updated ParameterPanel Layout

```
┌─ Simulation Controls ─────────────────────┐
│  City: [Bengaluru ▼]                      │
│  ─────────────────────────────────────── │
│  Presets: [Click to expand ▼]            │
│  ─────────────────────────────────────── │
│  Foreign Direct Investment                │
│  ├ IT/ITES       [=====●=========] +40% │
│  ├ Manufacturing  [=====●=========] +20% │
│  ├ Real Estate    [=====●=========]  0%  │
│  ├ Trade/Hospital [=====●=========] -10% │
│  ├ Transport/Logs [=====●=========] +15% │
│  └────────────────────────────────────── │
│  Policies (India Schemes)                 │
│  ├ [✓] SEZ Zone: [Electronic City ▼]    │
│  ├ [✓] Smart City Mission               │
│  ├ [ ] AMRUT                              │
│  ├ [✓] RERA Compliance                   │
│  └ [ ] PM Awas Yojana                     │
│  ─────────────────────────────────────── │
│  Climate: [✓] Monsoon Season              │
│  ─────────────────────────────────────── │
│  Horizon: [6m] [12m] [24m] [✓60m]        │
│  ─────────────────────────────────────── │
│  [▶ Run Simulation]                       │
└──────────────────────────────────────────┘
```

---

## 7. Implementation Roadmap

### Phase 0 — Data Pipeline (2 weeks)
| Task | Files | Depends On |
|------|-------|------------|
| 0.1 | City boundary GeoJSONs (12 cities) | `data/cities/*.geojson` | — |
| 0.2 | City config YAML files | `data/cities/*.yaml` | 0.1 |
| 0.3 | LULC → H3 aggregation script | `scripts/preprocess/lulc_to_h3.py` | 0.1 |
| 0.4 | Census → H3 population script | `scripts/preprocess/census_to_h3.py` | 0.1 |
| 0.5 | Night lights → economic baseline | `scripts/preprocess/nl_to_baseline.py` | 0.1 |
| 0.6 | SEZ boundary ingestion | `scripts/preprocess/sez_zones.py` | 0.1 |
| 0.7 | Slum boundary ingestion | `scripts/preprocess/slum_boundaries.py` | 0.1 |
| 0.8 | FDI historical data compilation | `data/fdi_india.csv` | — |
| 0.9 | Employment baseline compilation | `data/employment_baselines.py` | — |
| 0.10 | Indian case study data (12 entries) | `scripts/seed_case_studies.py` update | — |

### Phase 1 — Engine Rewrite (2 weeks)
| Task | Files | Depends On |
|------|-------|------------|
| 1.1 | Multi-sector GridState with new dimensions | `engine/grid.py` rewrite | 0.1-0.9 |
| 1.2 | Spatial heterogeneity init module | `engine/spatial_init.py` **NEW** | 1.1 |
| 1.3 | Primary loop: 7 sectors + informal economy | `engine/primary_loop.py` rewrite | 1.1 |
| 1.4 | Secondary loop: slum dynamics + multi-modal transit | `engine/secondary_loop.py` rewrite | 1.1-1.2 |
| 1.5 | Climate loop: monsoon + flood | `engine/climate_loop.py` **NEW** | 1.1 |
| 1.6 | Policy loop: SEZ, SmartCity, AMRUT, RERA, PMAY | `engine/policy_loop.py` **NEW** | 1.1-1.2 |
| 1.7 | Tertiary loop: Indian case study RAG | `engine/tertiary_loop.py` rewrite | 0.10 |
| 1.8 | Vectorize: k-d tree neighbor, public works, flood | `engine/grid.py` + `engine/primary_loop.py` | 1.1 |
| 1.9 | Runner: orchestrate 5 loops, deadline check | `engine/runner.py` rewrite | 1.3-1.7 |

### Phase 2 — Database & API (1 week)
| Task | Files | Depends On |
|------|-------|------------|
| 2.1 | Real Supabase integration (remove mock) | `app/db.py` rewrite | — |
| 2.2 | Region CRUD from DB | `app/routes/regions.py` | 0.1, 2.1 |
| 2.3 | Multi-region WebSocket handler | `app/ws/simulation.py` | 1.9, 2.1 |
| 2.4 | Policy param schema in API | `engine/models.py` update | 1.6 |
| 2.5 | Simulation persistence & historical queries | `app/routes/simulations.py` | 2.1 |

### Phase 3 — Frontend Overhaul (1.5 weeks)
| Task | Files | Depends On |
|------|-------|------------|
| 3.1 | City selector with live preview | `components/controls/CitySelector.tsx` **NEW** | 0.1 |
| 3.2 | 7-sector FDI sliders | `components/controls/FDISliders.tsx` | — |
| 3.3 | Policy panel | `components/controls/PolicyPanel.tsx` **NEW** | 2.4 |
| 3.4 | Monsoon toggle | `components/controls/MonsoonToggle.tsx` **NEW** | 1.5 |
| 3.5 | Map defaults for India, new overlays | `lib/mapConfig.ts`, `MapViewport.tsx` | 0.1, 0.6, 0.7 |
| 3.6 | New metric charts (6 new metrics) | `components/dashboard/MetricPanel.tsx` | 1.1 |
| 3.7 | India case study seed embed | `scripts/seed_case_studies.py` | 0.10 |
| 3.8 | A/B comparison UI | `components/controls/ABComparer.tsx` **NEW** | 2.1 |

### Phase 4 — Polish & Performance (1 week)
| Task | Files | Depends On |
|------|-------|------------|
| 4.1 | Benchmark 24-month sim for Mumbai (~1400 cells) | `tests/performance/` | 1.9 |
| 4.2 | Numba JIT for hot loops if needed | `engine/` | 4.1 |
| 4.3 | Reduce frame JSON size (orjson + binary) | `engine/serializer.py` | — |
| 4.4 | Permessage-deflate WS compression | `app/ws/simulation.py` | — |
| 4.5 | Indian Mapbox/CartoDB style | `lib/mapConfig.ts` | — |

### Phase 5 — Testing & Validation (1 week)
| Task | Files | Depends On |
|------|-------|------------|
| 5.1 | Unit tests: spatial_init, climate, policy loops | `tests/unit/` | 1.2-1.4 |
| 5.2 | Integration tests: full India sim cycle | `tests/integration/` | 2.3 |
| 5.3 | Calibration tests: compare output vs real India data | `tests/validation/` **NEW** | 0.9, 1.9 |
| 5.4 | 10-city load test | `tests/load/locustfile.py` update | 4.1-4.3 |
| 5.5 | E2E: frontend India workflow | `tests/e2e/` | 3.7 |

---

## 8. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Indian cities supported | 0 | 12 (4 P0, 4 P1, 4 P2) |
| Simulation sectors | 3 | 7 |
| Simulation dimensions per cell | 4 (E,K,R,T) | 8 (Ef,Ei,K,R,T,H,F,M) |
| Case studies | 0 Indian / 6 total | 12 Indian / 12 total |
| Policy interventions | 0 | 7 |
| Climate modeling | None | Monsoon + flood |
| Informal economy | Ignored | Explicitly modeled |
| 24-month sim perf (Bengaluru ~1800 cells) | ~1.2s | ≤ 800ms |
| Calibrated constants | 0 (all guessed) | Validated against Indian data ≥ 70% |
| Map center | NYC | Indian city selector |

---

## Appendix A — File Change Summary

| Action | File |
|--------|------|
| **REWRITE** | `backend/engine/grid.py` |
| **REWRITE** | `backend/engine/primary_loop.py` |
| **REWRITE** | `backend/engine/secondary_loop.py` |
| **REWRITE** | `backend/engine/tertiary_loop.py` |
| **REWRITE** | `backend/engine/runner.py` |
| **REWRITE** | `backend/engine/serializer.py` |
| **UPDATE** | `backend/engine/models.py` |
| **NEW** | `backend/engine/spatial_init.py` |
| **NEW** | `backend/engine/climate_loop.py` |
| **NEW** | `backend/engine/policy_loop.py` |
| **REWRITE** | `backend/app/db.py` |
| **UPDATE** | `backend/app/ws/simulation.py` |
| **UPDATE** | `backend/app/routes/regions.py` |
| **NEW** | `data/cities/*.yaml` (12 files) |
| **NEW** | `data/cities/*.geojson` (12 files) |
| **NEW** | `data/fdi_india.csv` |
| **NEW** | `scripts/preprocess/lulc_to_h3.py` |
| **NEW** | `scripts/preprocess/census_to_h3.py` |
| **NEW** | `scripts/preprocess/nl_to_baseline.py` |
| **NEW** | `scripts/preprocess/sez_zones.py` |
| **NEW** | `scripts/preprocess/slum_boundaries.py` |
| **REWRITE** | `scripts/seed_case_studies.py` |
| **UPDATE** | `frontend/src/lib/mapConfig.ts` |
| **UPDATE** | `frontend/src/components/controls/FDISliders.tsx` |
| **UPDATE** | `frontend/src/components/controls/ParameterPanel.tsx` |
| **UPDATE** | `frontend/src/components/dashboard/MetricPanel.tsx` |
| **UPDATE** | `frontend/src/components/map/MapViewport.tsx` |
| **NEW** | `frontend/src/components/controls/CitySelector.tsx` |
| **NEW** | `frontend/src/components/controls/PolicyPanel.tsx` |
| **NEW** | `frontend/src/components/controls/MonsoonToggle.tsx` |
| **NEW** | `frontend/src/components/controls/ABComparer.tsx` |
| **UPDATE** | `frontend/src/types/simulation.ts` |
| **UPDATE** | `frontend/src/store/simulationStore.ts` |

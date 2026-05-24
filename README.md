<p align="center">
  <br/>
  <br/>

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ███╗   ███╗ ███████╗ ████████╗ ██████╗  ██████╗ ██████╗  ██╗   ██╗██╗     ║
║   ████╗ ████║ ██╔════╝ ╚══██╔══╝ ██╔══██╗██╔═══██╗██╔══██╗ ██║   ██║██║     ║
║   ██╔████╔██║ █████╗      ██║    ██████╔╝██║   ██║██████╔╝ ██║   ██║██║     ║
║   ██║╚██╔╝██║ ██╔══╝      ██║    ██╔══██╗██║   ██║██╔═══╝  ╚██╗ ██╔╝██║     ║
║   ██║ ╚═╝ ██║ ███████╗    ██║    ██║  ██║╚██████╔╝██║       ╚████╔╝ ███████╗║
║   ╚═╝     ╚═╝ ╚══════╝    ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═══╝  ╚══════╝║
║                                                                               ║
║              ██████╗ ██╗   ██╗██╗     ███████╗███████╗███████╗               ║
║              ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝██╔════╝               ║
║              ██████╔╝██║   ██║██║     █████╗  ███████╗█████╗                 ║
║              ██╔═══╝ ██║   ██║██║     ██╔══╝  ╚════██║██╔══╝                 ║
║              ██║     ╚██████╔╝███████╗███████╗███████║███████╗               ║
║              ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

  <h3 align="center">AI-Powered Macro-Urban Digital Twin Sandbox</h3>

  <p align="center">
    Simulate the economic ripple effects of policy decisions across cities using
    <br/>
    H3 hexagonal grids, agent-based modeling, and real-time visualization.
    <br/>
    <br/>
    <a href="#getting-started"><strong>Get Started »</strong></a>
    &nbsp;&middot;&nbsp;
    <a href="#architecture"><strong>Architecture</strong></a>
    &nbsp;&middot;&nbsp;
    <a href="#api-reference"><strong>API</strong></a>
    &nbsp;&middot;&nbsp;
    <a href="#roadmap"><strong>Roadmap</strong></a>
  </p>

  <p align="center">
    <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
    <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python" alt="Python" />
    <img src="https://img.shields.io/badge/TypeScript-5.4-3178C6?logo=typescript" alt="TypeScript" />
    <img src="https://img.shields.io/badge/Deck.gl-9.0-5B21D6" alt="Deck.gl" />
    <img src="https://img.shields.io/badge/H3-4.0-1A73E8?logo=uber" alt="H3" />
    <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase" alt="Supabase" />
    <img src="https://img.shields.io/badge/License-MIT-green" alt="License" />
  </p>
</p>

---

## Table of Contents

- [What is MetroPulse?](#what-is-metropulse)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Simulation Engine](#simulation-engine)
- [Testing](#testing)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is MetroPulse?

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                                                                 │
   │    💰 FDI Investment                                           │
   │        │                                                        │
   │        ▼                                                        │
   │    ┌────────┐     ┌────────────┐     ┌────────────────┐        │
   │    │ PRIMARY │────▶│ SECONDARY  │────▶│   TERTIARY     │        │
   │    │  LOOP   │     │   LOOP     │     │    LOOP        │        │
   │    │(Direct) │     │(Cascading) │     │ (AI Insights)  │        │
   │    └────────┘     └────────────┘     └────────────────┘        │
   │        │                │                     │                 │
   │        ▼                ▼                     ▼                 │
   │   Employment      Real Estate           RAG + LLM              │
   │   GDP Impact      Transit Flow          Policy Analysis        │
   │   Capital         Congestion            Case Studies            │
   │   Formation       Spillover             Narrative               │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
```

**MetroPulse** is a real-time urban simulation platform that models how economic shocks
— foreign direct investment, public infrastructure, policy changes — propagate through
a city's hexagonal grid over time. It combines:

- **Physics-inspired simulation loops** (direct impacts, cascading effects, AI narrative)
- **H3 hexagonal spatial indexing** for granular geographic analysis
- **Real-time WebSocket streaming** of simulation frames to a 3D map
- **LLM-powered insights** (OpenAI, Gemini, Ollama) with RAG from urban case studies

Think of it as a *flight simulator for urban policy*.

---

## Key Features

```
  ╔═══════════════════════════════╦═══════════════════════════════════╗
  ║      SIMULATION ENGINE        ║          FRONTEND                 ║
  ╠═══════════════════════════════╬═══════════════════════════════════╣
  ║                               ║                                   ║
  ║  ◆ 3-Loop Cascade Model      ║  ◆ 3D Hex Map (Deck.gl + MapLibre)║
  ║  ◆ H3 Resolution 8 Grid      ║  ◆ Real-time WebSocket Frames    ║
  ║  ◆ NumPy Vectorized Ops      ║  ◆ Drawing Tools (Pin/Polygon)   ║
  ║  ◆ Multi-Provider LLM        ║  ◆ Frame Scrubber Timeline       ║
  ║  ◆ RAG Case Study Search     ║  ◆ Interactive FDI Sliders       ║
  ║  ◆ Spatial Spillover Model   ║  ◆ 6 Scenario Presets            ║
  ║  ◆ 6 Economic Sectors        ║  ◆ Live Metric Dashboard         ║
  ║  ◆ Public Works Boost        ║  ◆ AI Insight Panel (Streaming)  ║
  ║  ◆ Supabase PostgreSQL       ║  ◆ Responsive + Keyboard Shortcuts║
  ║  ◆ pgvector Embeddings       ║  ◆ Export Results as JSON        ║
  ║                               ║                                   ║
  ╚═══════════════════════════════╩═══════════════════════════════════╝
```

---

## Architecture

```
                        ┌──────────────────────────────────┐
                        │          FRONTEND (Next.js)      │
                        │                                  │
                        │  ┌─────────┐   ┌──────────────┐ │
                        │  │ MapLibre │   │  Zustand     │ │
                        │  │ + Deck.gl│   │  Store       │ │
                        │  └────┬────┘   └──────┬───────┘ │
                        │       │               │          │
                        │  ┌────┴───────────────┴───────┐ │
                        │  │      React Components       │ │
                        │  │  MapViewport · MetricPanel   │ │
                        │  │  ParameterPanel · AIInsight   │ │
                        │  └────────────┬────────────────┘ │
                        └───────────────┼──────────────────┘
                                        │
                          WebSocket + REST (port 3000 → 8000)
                                        │
                        ┌───────────────┼──────────────────┐
                        │          BACKEND (FastAPI)        │
                        │               │                   │
                        │  ┌────────────┴────────────────┐ │
                        │  │   /ws/simulate (WebSocket)   │ │
                        │  │   /api/regions  (REST)       │ │
                        │  │   /api/simulations (REST)    │ │
                        │  └────────────┬────────────────┘ │
                        │               │                   │
                        │  ┌────────────┴────────────────┐ │
                        │  │     SIMULATION ENGINE        │ │
                        │  │                              │ │
                        │  │  ┌──────────┐  ┌──────────┐ │ │
                        │  │  │ Primary   │  │ Secondary│ │ │
                        │  │  │ Loop      │─▶│ Loop     │ │ │
                        │  │  │ (Direct)  │  │(Cascade) │ │ │
                        │  │  └──────────┘  └────┬─────┘ │ │
                        │  │                     │       │ │
                        │  │              ┌──────┴─────┐ │ │
                        │  │              │  Tertiary   │ │ │
                        │  │              │  Loop (AI)  │ │ │
                        │  │              └────────────┘ │ │
                        │  │                              │ │
                        │  │  ┌──────────┐  ┌──────────┐ │ │
                        │  │  │ H3 Grid  │  │ Runner   │ │ │
                        │  │  │ State    │  │ (Orch.)  │ │ │
                        │  │  └──────────┘  └──────────┘ │ │
                        │  └─────────────────────────────┘ │
                        │                                   │
                        │  ┌─────────────────────────────┐ │
                        │  │   Supabase PostgreSQL        │ │
                        │  │   + pgvector (embeddings)    │ │
                        │  └─────────────────────────────┘ │
                        └───────────────────────────────────┘
```

### Simulation Loop Pipeline

```
  ┌───────────────────────────────────────────────────────────────────────┐
  │                                                                       │
  │  STEP 1: PRIMARY LOOP (Direct Impacts)                               │
  │  ────────────────────────────────                                     │
  │                                                                       │
  │  For each hex cell c:                                                 │
  │                                                                       │
  │    ΔK(c) = FDI_rate × sector_weight(c) × K(c)                       │
  │    ΔE(c) = α × ΔK(c) × employment_elasticity                        │
  │    Boost  = public_works_zone_bonus                                   │
  │                                                                       │
  │  ─────────────────────────────────────────────                        │
  │  STEP 2: SECONDARY LOOP (Cascading Effects)                          │
  │  ────────────────────────────────                                     │
  │                                                                       │
  │    ΔR(c) = γ × Σ_neighbors[ΔK × exp(-d/λ)]   (real estate)         │
  │    ΔT(c) = δ × ΔE / capacity                  (transit congestion)  │
  │                                                                       │
  │  ─────────────────────────────────────────────                        │
  │  STEP 3: TERTIARY LOOP (RAG + LLM Narrative)                         │
  │  ────────────────────────────────                                     │
  │                                                                       │
  │    1. Serialize frame → pgvector embedding                           │
  │    2. Search case studies via cosine similarity                      │
  │    3. Prompt LLM with context + case studies                         │
  │    4. Stream insight back to frontend                                │
  │                                                                       │
  └───────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 + React 18 | App framework, SSR, routing |
| **UI** | Tailwind CSS + Tremor | Styling + dashboard components |
| **Map** | MapLibre GL JS + Deck.gl | 3D hex visualization (no API key needed) |
| **State** | Zustand | Lightweight global state |
| **Backend** | FastAPI + Uvicorn | Async REST + WebSocket API |
| **Engine** | NumPy + SciPy | Vectorized simulation math |
| **Spatial** | H3 (v4) | Hexagonal spatial indexing |
| **Database** | Supabase PostgreSQL + pgvector | Persistence + vector search |
| **LLM** | OpenAI / Gemini / Ollama | AI insights with RAG |
| **Testing** | Pytest + Locust + Jest | Unit, integration, load tests |
| **Deploy** | Docker + Fly.io + Vercel | Backend + frontend hosting |
| **CI/CD** | GitHub Actions | Automated pipelines |

---

## Getting Started

### Prerequisites

```
  ┌────────────────────────────────────────────────────────┐
  │  You'll need:                                          │
  │                                                        │
  │    ✓  Python 3.11+                                     │
  │    ✓  Node.js 18+                                      │
  │    ✓  Git                                              │
  │    ✓  (Optional) Supabase account                      │
  │    ✓  (Optional) OpenAI / Gemini API key               │
  └────────────────────────────────────────────────────────┘
```

### 1. Clone the Repository

```bash
git clone https://github.com/MrNK2107/MetroPulse.git
cd MetroPulse
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your Supabase + LLM keys

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### 4. Open the App

Navigate to **http://localhost:3000** — you'll see the map, parameter panel, and dashboard.

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  ┌─ Sidebar ──────┐  ┌─ Map ──────────────────────────────┐   │
  │  │ Region: NYC     │  │                                    │   │
  │  │ FDI Sliders     │  │     ◇  ◇  ◇                       │   │
  │  │ Presets         │  │   ◇  ████  ◇  ◇                   │   │
  │  │ Draw Zones      │  │     ██████                         │   │
  │  │ Horizon         │  │   ◇  ████  ◇                      │   │
  │  │                 │  │     ◇  ◇                           │   │
  │  │ [Run Simulation]│  │                                    │   │
  │  └─────────────────┘  └────────────────────────────────────┘   │
  │  ┌─ Dashboard ─────────────────────────────────────────────┐   │
  │  │ GDP │ Unemployment │ Real Estate │ Transit │ AI Insight │   │
  │  └─────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
MetroPulse/
│
├── backend/                          # FastAPI + Simulation Engine
│   ├── app/
│   │   ├── routes/                   # REST endpoints
│   │   │   ├── health.py             #   GET /health
│   │   │   ├── regions.py            #   GET /api/regions
│   │   │   ├── simulations.py        #   POST /api/simulations
│   │   │   └── case_studies.py       #   GET /api/case-studies
│   │   ├── ws/
│   │   │   └── simulation.py         #   WS /ws/simulate
│   │   ├── config.py                 # Pydantic settings
│   │   ├── db.py                     # Supabase client
│   │   └── main.py                   # FastAPI app factory
│   │
│   ├── engine/                       # Core Simulation
│   │   ├── grid.py                   #   H3 grid state management
│   │   ├── primary_loop.py           #   Direct economic impacts
│   │   ├── secondary_loop.py         #   Cascading spatial effects
│   │   ├── tertiary_loop.py          #   RAG + LLM narrative gen
│   │   ├── runner.py                 #   Simulation orchestrator
│   │   ├── serializer.py             #   Frame serialization
│   │   └── models.py                 #   Pydantic schemas
│   │
│   ├── tests/
│   │   ├── unit/                     # Grid, loops, serializer tests
│   │   ├── integration/              # REST + WebSocket tests
│   │   └── load/                     # Locust performance tests
│   │
│   ├── Dockerfile                    # Fly.io container
│   ├── fly.toml                      # Deployment config
│   ├── pyproject.toml                # Python project metadata
│   └── requirements.txt              # Pinned dependencies
│
├── frontend/                         # Next.js 14 App
│   ├── src/
│   │   ├── app/
│   │   │   └── page.tsx              # Main page layout
│   │   ├── components/
│   │   │   ├── map/                  #   MapViewport, HexLayer, DrawingToolbar
│   │   │   ├── controls/             #   ParameterPanel, FDISliders, Presets
│   │   │   ├── dashboard/            #   MetricPanel, AIInsightPanel
│   │   │   └── shared/               #   LoadingOverlay
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts       #   WS connection hook
│   │   ├── lib/
│   │   │   ├── ws.ts                 #   WebSocket client
│   │   │   ├── api.ts                #   REST client
│   │   │   ├── mapConfig.ts          #   Map defaults + cities
│   │   │   └── colorScale.ts         #   Hex color interpolation
│   │   ├── store/
│   │   │   └── simulationStore.ts    #   Zustand state
│   │   └── types/
│   │       └── simulation.ts         #   TypeScript interfaces
│   │
│   ├── package.json
│   └── tsconfig.json
│
├── scripts/
│   ├── seed_case_studies.py          # Seed RAG case studies
│   └── seed_cities.py                # Seed city boundaries
│
├── supabase/
│   └── migrations/                   # Database schema
│
├── .github/
│   └── workflows/                    # CI/CD pipelines
│
├── docs/
│   └── INDIA_OVERHAUL_PLAN.md        # India expansion roadmap
│
├── AGENTS.md                         # AI agent context
└── README.md                         # You are here
```

---

## API Reference

### REST Endpoints

```
┌──────────┬────────────────────────────┬──────────────────────────────────┐
│  Method  │  Endpoint                  │  Description                     │
├──────────┼────────────────────────────┼──────────────────────────────────┤
│  GET     │  /health                   │  Health check                    │
│  GET     │  /api/regions              │  List available city regions     │
│  GET     │  /api/regions/{id}         │  Get region baseline data        │
│  POST    │  /api/simulations          │  Create simulation run           │
│  GET     │  /api/simulations/{id}     │  Get simulation results          │
│  GET     │  /api/case-studies         │  List RAG case studies           │
│  WS      │  /ws/simulate              │  Real-time simulation stream     │
└──────────┴────────────────────────────┴──────────────────────────────────┘
```

### Response Envelope

All REST responses follow a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "timestamp": "2026-05-27T..." }
}
```

### WebSocket Protocol

Connect to `ws://localhost:8000/ws/simulate` and send:

```json
{
  "region_id": "nyc_manhattan",
  "fdi_inputs": { "technology": 0.4, "manufacturing": 0.2, "services": 0.1 },
  "public_works_zones": [{ "type": "Polygon", "coordinates": [...] }],
  "horizon_months": 24
}
```

Receive streamed frames:

```json
{
  "type": "frame",
  "step": 1,
  "total_steps": 24,
  "cells": [
    { "h3": "882a100e3fffff", "delta": 0.12, "economic_activity": 5400, ... }
  ],
  "metrics": { "gdp_delta": 0.08, "unemployment": 0.045, ... }
}
```

---

## Simulation Engine

### Three-Loop Cascade Model

```
           ┌─────────────────────────────────────────────────────┐
           │                                                     │
           │    TIME ──────────────────────────────────────▶     │
           │                                                     │
           │    t=0          t=1          t=2          t=T       │
           │     │            │            │            │        │
           │     ▼            ▼            ▼            ▼        │
           │   ┌────┐      ┌────┐      ┌────┐      ┌────┐      │
           │   │ P  │      │ P  │      │ P  │      │ P  │      │
           │   │    │      │    │      │    │      │    │      │
           │   │ S  │      │ S  │      │ S  │      │ S  │      │
           │   │    │      │    │      │    │      │    │      │
           │   │ T  │      │ T  │      │ T  │      │ T  │      │
           │   └────┘      └────┘      └────┘      └────┘      │
           │                                                     │
           │   P = Primary  (FDI → Employment, Capital)          │
           │   S = Secondary (Capital → Real Estate, Transit)    │
           │   T = Tertiary  (Metrics → LLM Narrative)           │
           │                                                     │
           └─────────────────────────────────────────────────────┘
```

### Sectors Modeled

| Sector | Description | Weight |
|--------|-------------|--------|
| Technology | Software, IT services, startups | 0.30 |
| Manufacturing | Industrial production, logistics | 0.25 |
| Services | Finance, healthcare, education | 0.20 |
| Real Estate | Property development, housing | 0.10 |
| Energy | Power, renewables, utilities | 0.08 |
| Agriculture | Food processing, rural linkages | 0.07 |

### Metrics Tracked

```
  ┌────────────────────────────────────────────────────────────────────┐
  │                                                                    │
  │   GDP Delta          Unemployment Rate     Real Estate Index       │
  │   ╭───╮              ╭───╮                 ╭───╮                   │
  │   │ ↑ │  +8.2%       │ ↓ │  4.5%          │ ↑ │  1.12             │
  │   ╰───╯              ╰───╯                 ╰───╯                   │
  │                                                                    │
  │   Transit Congestion   Frame N / M       AI Insight                │
  │   ╭───╮                ╭───╮             ╭─────────────────────╮   │
  │   │ ↑ │  0.67          │24/│ 24          │ The 40% increase... │   │
  │   ╰───╯                ╰───╯             ╰─────────────────────╯   │
  │                                                                    │
  └────────────────────────────────────────────────────────────────────┘
```

---

## Testing

```bash
# Backend unit tests
cd backend && pytest tests/unit/ -v

# Backend integration tests
cd backend && pytest tests/integration/ -v

# Backend load tests
cd backend && locust -f tests/load/locustfile.py --host http://localhost:8000

# Frontend tests
cd frontend && npm run test

# Lint + type check
cd frontend && npm run lint && npm run type-check
```

```
  ┌─────────────────────────────────────────────────────┐
  │  Test Coverage                                      │
  │                                                     │
  │  Unit Tests        ████████████████████░░  90%      │
  │  Integration       ████████████████░░░░░░  75%      │
  │  Load Tests        ██████████░░░░░░░░░░░░  50%      │
  │  Frontend          ░░░░░░░░░░░░░░░░░░░░░░   0%      │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

---

## Deployment

### Backend (Fly.io)

```bash
cd backend
fly deploy
```

### Frontend (Vercel)

```bash
cd frontend
vercel --prod
```

### Docker

```bash
cd backend
docker build -t metropulse-backend .
docker run -p 8000:8000 metropulse-backend
```

---

## Roadmap

```
  Phase 0: Scaffold          ████████████████████  COMPLETE
  Phase 1: Engine             ████████████████████  COMPLETE
  Phase 2: API Layer          ████████████████████  COMPLETE
  Phase 3: Map Shell          ████████████████████  COMPLETE
  Phase 4: WebSocket          ████████████████████  COMPLETE
  Phase 5: Controls           ████████████████████  COMPLETE
  Phase 6: RAG + AI           ████████████████████  COMPLETE
  Phase 7: Loading States     ████████████████████  COMPLETE
  Phase 8: Polish & UI        ████████████████████  COMPLETE
  Phase 9: Testing            ████████████████████  COMPLETE
  Phase 10: Deployment        ████████████████████  COMPLETE
  ─────────────────────────────────────────────────────────────
  India Overhaul (Planned):
  Phase 0: Data Pipeline      ░░░░░░░░░░░░░░░░░░░░  PLANNED
  Phase 1: Engine Rewrite     ░░░░░░░░░░░░░░░░░░░░  PLANNED
  Phase 2: Database & API     ░░░░░░░░░░░░░░░░░░░░  PLANNED
  Phase 3: Frontend Overhaul  ░░░░░░░░░░░░░░░░░░░░  PLANNED
  Phase 4: Performance        ░░░░░░░░░░░░░░░░░░░░  PLANNED
  Phase 5: Validation         ░░░░░░░░░░░░░░░░░░░░  PLANNED
```

### Upcoming India Expansion

- **12 Indian cities** (Bengaluru, Mumbai, Delhi NCR, Chennai, Hyderabad, Pune, Kolkata, Ahmedabad, Lucknow, Jaipur, Chandigarh, Bhubaneswar)
- **7-sector model** (IT/ITES, Manufacturing, Real Estate, Trade, Transport, Informal, Public Admin)
- **Monsoon + flood climate modeling**
- **Policy interventions** (SEZ, Smart City Mission, AMRUT, RERA, PM Awas Yojana)
- **Informal economy modeling** (80%+ of Indian urban employment)

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat(scope): add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

### Commit Convention

```
feat(scope): description     # New feature
fix(scope): description      # Bug fix
refactor(scope): description # Code refactor
test(scope): description     # Adding tests
docs(scope): description     # Documentation
```

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                      Built with passion for urban futures                     ║
║                                                                               ║
║     MetroPulse — Where data meets geography, and policy meets prediction.    ║
║                                                                               ║
║                         github.com/MrNK2107/MetroPulse                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

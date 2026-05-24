<div align="center">

```text
███╗   ███╗███████╗████████╗██████╗  ██████╗ ██████╗ ██╗   ██╗██╗     ███████╗███████╗
████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗██╔══██╗██║   ██║██║     ██╔════╝██╔════╝
██╔████╔██║█████╗     ██║   ██████╔╝██║   ██║██████╔╝██║   ██║██║     ███████╗█████╗  
██║╚██╔╝██║██╔══╝     ██║   ██╔══██╗██║   ██║██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  
██║ ╚═╝ ██║███████╗   ██║   ██║  ██║╚██████╔╝██║     ╚██████╔╝███████╗███████║███████╗
╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝
```

# MetroPulse

### AI-Powered Macro-Urban Digital Twin Sandbox

```diff
+ Simulate cities before governments change them.
+ Predict economic ripple effects before policies become reality.
+ Stream urban futures in real time.
```

<img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js&style=for-the-badge" />
<img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&style=for-the-badge" />
<img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&style=for-the-badge" />
<img src="https://img.shields.io/badge/TypeScript-5.4-3178C6?logo=typescript&style=for-the-badge" />
<img src="https://img.shields.io/badge/H3-Hex_Engine-1A73E8?logo=uber&style=for-the-badge" />
<img src="https://img.shields.io/badge/AI-RAG_+_LLM-ffcc00?style=for-the-badge" />
<img src="https://img.shields.io/badge/Streaming-WebSocket-0099ff?style=for-the-badge" />
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />

<br/>
<br/>

> A flight simulator for urban policy.

</div>

---

## ◉ System Boot

```text
[ MetroPulse Kernel v0.9.4 ]
────────────────────────────────────────────────────────────

Initializing spatial grid engine...
Loading H3 hexagonal city topology...
Mounting economic sector matrices...
Loading transit pressure model...
Loading real estate spillover model...
Connecting vector memory...
Starting AI insight subsystem...
Opening simulation websocket...

STATUS: ONLINE
```

---

## What is MetroPulse?

MetroPulse is a real-time urban simulation platform that models how economic shocks, policy decisions, infrastructure projects, and investment flows spread across a city.

It uses **H3 hexagonal grids**, **agent-inspired simulation loops**, **FastAPI WebSocket streaming**, and **LLM-powered narrative analysis** to show how one decision can create cascading effects across employment, GDP, real estate, transit, migration, and public infrastructure.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   FDI Investment                                                         │
│       │                                                                  │
│       ▼                                                                  │
│   ┌────────────┐     ┌──────────────┐     ┌────────────────────┐         │
│   │  PRIMARY   │────▶│  SECONDARY   │────▶│     TERTIARY       │         │
│   │   LOOP     │     │    LOOP      │     │      LOOP          │         │
│   │  Direct    │     │  Cascading   │     │   AI Insights      │         │
│   └────────────┘     └──────────────┘     └────────────────────┘         │
│       │                    │                         │                   │
│       ▼                    ▼                         ▼                   │
│   Employment          Real Estate              RAG + LLM                 │
│   GDP Impact          Transit Flow             Policy Analysis           │
│   Capital Growth      Congestion               Case Studies              │
│   Sector Boost        Spillover                Narrative Output          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

Think of it as:

```text
SimCity + Digital Twin + Economic Policy Lab + AI Analyst
```

---

## Why MetroPulse Exists

Modern cities are too complex for static spreadsheets.

A single policy decision can:

- increase GDP,
- overload transport systems,
- raise housing prices,
- create employment clusters,
- displace vulnerable communities,
- attract further investment,
- or trigger hidden second-order effects.

Yet most urban decisions are still evaluated using fragmented reports, slow dashboards, and isolated datasets.

MetroPulse turns urban policy into an interactive simulation sandbox.

```text
Cities are living systems.

Every investment creates movement.
Every policy creates pressure.
Every decision creates ripple effects.

MetroPulse simulates those ripples.
```

---

## Core Features

```text
╔════════════════════════════════════════╦══════════════════════════════════════════╗
║          SIMULATION ENGINE             ║               FRONTEND                  ║
╠════════════════════════════════════════╬══════════════════════════════════════════╣
║                                        ║                                          ║
║   ◆ 3-Loop Cascade Model              ║   ◆ 3D Hex Map                           ║
║   ◆ H3 Resolution Grid                ║   ◆ Deck.gl + MapLibre                   ║
║   ◆ NumPy Vectorized Simulation       ║   ◆ Real-time WebSocket Frames           ║
║   ◆ Spatial Spillover Model           ║   ◆ Drawing Tools                        ║
║   ◆ Sector-Based Economic Weights     ║   ◆ FDI Sliders                          ║
║   ◆ Public Works Zone Boosts          ║   ◆ Timeline Scrubber                    ║
║   ◆ Transit Pressure Modeling         ║   ◆ Live Metric Dashboard                ║
║   ◆ Real Estate Ripple Effects        ║   ◆ AI Insight Panel                     ║
║   ◆ RAG Case Study Search             ║   ◆ Export Simulation Results            ║
║   ◆ Multi-Provider LLM Support        ║   ◆ Keyboard Shortcuts                   ║
║                                        ║                                          ║
╚════════════════════════════════════════╩══════════════════════════════════════════╝
```

---

## Live Simulation Feed

```text
TIME: 2032-07-14 08:42 UTC
REGION: Bengaluru Urban Corridor
EVENT: +40% Technology FDI Injection

┌─────────────────────────────────────────────┐
│ GDP Growth             ▲ +8.2%              │
│ Employment             ▲ +5.4%              │
│ Real Estate Index      ▲ +12.1%             │
│ Transit Congestion     ▲ +18.7%             │
│ Informal Migration     ▲ +7.9%              │
└─────────────────────────────────────────────┘

Hex Activity Heatmap:

░░░░▒▒▒▒▓▓▓████████▓▓▒▒▒░░
░░▒▒▓▓████████████████▓▒▒░
▒▒▓█████████████████████▓▒
▓████████████████████████▓
▓████████████████████████▓
▒▓██████████████████████▓▒
░▒▓████████████████████▓▒░
░░▒▒▓▓██████████████▓▓▒▒░░
```

---

## System Architecture

```text
                         ┌───────────────────────────────────────┐
                         │           FRONTEND                    │
                         │           Next.js 14                  │
                         │                                       │
                         │  ┌───────────┐    ┌───────────────┐   │
                         │  │ MapLibre  │    │   Zustand     │   │
                         │  │ + Deck.gl │    │   Store       │   │
                         │  └─────┬─────┘    └───────┬───────┘   │
                         │        │                  │           │
                         │  ┌─────▼──────────────────▼────────┐  │
                         │  │       React Components           │  │
                         │  │ MapViewport · MetricPanel        │  │
                         │  │ ParameterPanel · AIInsight       │  │
                         │  └──────────────┬──────────────────┘  │
                         └─────────────────┼─────────────────────┘
                                           │
                              WebSocket + REST API
                                           │
                         ┌─────────────────▼─────────────────────┐
                         │              BACKEND                  │
                         │              FastAPI                  │
                         │                                       │
                         │  ┌─────────────────────────────────┐  │
                         │  │ /ws/simulate                    │  │
                         │  │ /api/regions                    │  │
                         │  │ /api/simulations                │  │
                         │  │ /api/case-studies               │  │
                         │  └──────────────┬──────────────────┘  │
                         │                 │                     │
                         │  ┌──────────────▼──────────────────┐  │
                         │  │       SIMULATION ENGINE          │  │
                         │  │                                  │  │
                         │  │  ┌───────────┐   ┌───────────┐   │  │
                         │  │  │ Primary   │──▶│ Secondary │   │  │
                         │  │  │ Loop      │   │ Loop      │   │  │
                         │  │  └───────────┘   └─────┬─────┘   │  │
                         │  │                        │         │  │
                         │  │                  ┌─────▼─────┐   │  │
                         │  │                  │ Tertiary  │   │  │
                         │  │                  │ AI Loop   │   │  │
                         │  │                  └───────────┘   │  │
                         │  │                                  │  │
                         │  │  ┌───────────┐   ┌───────────┐   │  │
                         │  │  │ H3 Grid   │   │ Runner    │   │  │
                         │  │  │ State     │   │ Orchestr. │   │  │
                         │  │  └───────────┘   └───────────┘   │  │
                         │  └──────────────────────────────────┘  │
                         │                                       │
                         │  ┌──────────────────────────────────┐  │
                         │  │ Supabase PostgreSQL + pgvector   │  │
                         │  └──────────────────────────────────┘  │
                         └───────────────────────────────────────┘
```

---

## Simulation Pipeline

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  STEP 1 — PRIMARY LOOP                                                        │
│  Direct economic impact                                                       │
│                                                                              │
│    FDI → Capital Formation → Employment → GDP Growth                         │
│                                                                              │
│  STEP 2 — SECONDARY LOOP                                                      │
│  Spatial and economic spillover                                               │
│                                                                              │
│    Capital Growth → Real Estate Pressure → Transit Congestion                │
│                                                                              │
│  STEP 3 — TERTIARY LOOP                                                       │
│  AI interpretation and narrative intelligence                                 │
│                                                                              │
│    Frame Metrics → Vector Search → Case Studies → LLM Insight                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Economic Propagation Model

```text
FDI Injection
      │
      ▼
Capital Formation
      │
      ▼
Employment Expansion
      │
      ▼
Consumer Spending
      │
      ▼
Transit Load Increase
      │
      ▼
Real Estate Pressure
      │
      ▼
Migration Spillover
      │
      ▼
AI Narrative Generation
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript |
| UI | Tailwind CSS, Tremor |
| Mapping | MapLibre GL JS, Deck.gl |
| Spatial Indexing | H3 |
| Backend | FastAPI, Uvicorn |
| Simulation | Python, NumPy, SciPy |
| Database | Supabase PostgreSQL |
| Vector Search | pgvector |
| AI Layer | OpenAI, Gemini, Ollama |
| State Management | Zustand |
| Streaming | WebSockets |
| Testing | Pytest, Jest, Locust |
| Deployment | Docker, Fly.io, Vercel |
| CI/CD | GitHub Actions |

---

## Mission Control Preview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ METROPULSE MISSION CONTROL                                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ REGION             Mumbai Metropolitan Region                                │
│ SIMULATION MODE    FDI Shock + Public Works Boost                            │
│ HORIZON            24 Months                                                 │
│ STATUS             Running                                                   │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ GDP Delta              ██████████████████░░░░░░░░     +8.2%                 │
│ Employment Growth      ███████████████░░░░░░░░░░░     +5.4%                 │
│ Real Estate Pressure   █████████████████████░░░░░     +12.1%                │
│ Transit Congestion     ███████████████████████░░░     +18.7%                │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ AI INSIGHT                                                                    │
│                                                                              │
│ The eastern industrial corridor shows accelerated employment clustering,      │
│ but rising real estate pressure may create displacement risk after month 18.  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```text
MetroPulse/
│
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── regions.py
│   │   │   ├── simulations.py
│   │   │   └── case_studies.py
│   │   ├── ws/
│   │   │   └── simulation.py
│   │   ├── config.py
│   │   ├── db.py
│   │   └── main.py
│   │
│   ├── engine/
│   │   ├── grid.py
│   │   ├── primary_loop.py
│   │   ├── secondary_loop.py
│   │   ├── tertiary_loop.py
│   │   ├── runner.py
│   │   ├── serializer.py
│   │   └── models.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── load/
│   │
│   ├── Dockerfile
│   ├── fly.toml
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── map/
│   │   │   ├── controls/
│   │   │   ├── dashboard/
│   │   │   └── shared/
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   ├── lib/
│   │   │   ├── ws.ts
│   │   │   ├── api.ts
│   │   │   ├── mapConfig.ts
│   │   │   └── colorScale.ts
│   │   ├── store/
│   │   │   └── simulationStore.ts
│   │   └── types/
│   │       └── simulation.ts
│   │
│   ├── package.json
│   └── tsconfig.json
│
├── scripts/
│   ├── seed_case_studies.py
│   └── seed_cities.py
│
├── supabase/
│   └── migrations/
│
├── docs/
│   └── INDIA_OVERHAUL_PLAN.md
│
├── .github/
│   └── workflows/
│
├── AGENTS.md
└── README.md
```

---

## Getting Started

### Prerequisites

```text
┌────────────────────────────────────────────────────────────┐
│ Required                                                   │
├────────────────────────────────────────────────────────────┤
│ Python 3.11+                                               │
│ Node.js 18+                                                │
│ Git                                                        │
│ npm or pnpm                                                │
│                                                            │
│ Optional                                                   │
├────────────────────────────────────────────────────────────┤
│ Supabase account                                           │
│ OpenAI API key                                             │
│ Gemini API key                                             │
│ Ollama local model                                         │
└────────────────────────────────────────────────────────────┘
```

---

### 1. Clone the Repository

```bash
git clone https://github.com/MrNK2107/MetroPulse.git
cd MetroPulse
```

---

### 2. Backend Setup

```bash
cd backend

python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"

cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

Backend runs at:

```text
http://localhost:8000
```

---

### 3. Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:3000
```

---

## Environment Variables

Create a `.env` file inside `backend/`.

```env
SUPABASE_URL=
SUPABASE_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
DATABASE_URL=
```

For local-only development, LLM and Supabase integrations can be disabled or mocked depending on your implementation.

---

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/regions` | List available city regions |
| GET | `/api/regions/{id}` | Get region baseline data |
| POST | `/api/simulations` | Create simulation run |
| GET | `/api/simulations/{id}` | Get simulation results |
| GET | `/api/case-studies` | List RAG case studies |
| WS | `/ws/simulate` | Real-time simulation stream |

---

## Response Envelope

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "timestamp": "2026-05-27T00:00:00Z"
  }
}
```

---

## WebSocket Protocol

Connect to:

```text
ws://localhost:8000/ws/simulate
```

Send:

```json
{
  "region_id": "nyc_manhattan",
  "fdi_inputs": {
    "technology": 0.4,
    "manufacturing": 0.2,
    "services": 0.1
  },
  "public_works_zones": [
    {
      "type": "Polygon",
      "coordinates": []
    }
  ],
  "horizon_months": 24
}
```

Receive:

```json
{
  "type": "frame",
  "step": 1,
  "total_steps": 24,
  "cells": [
    {
      "h3": "882a100e3fffff",
      "delta": 0.12,
      "economic_activity": 5400
    }
  ],
  "metrics": {
    "gdp_delta": 0.08,
    "unemployment": 0.045,
    "real_estate_index": 1.12,
    "transit_congestion": 0.67
  }
}
```

---

## Sectors Modeled

| Sector | Description | Weight |
|---|---|---:|
| Technology | Software, IT services, startups | 0.30 |
| Manufacturing | Industrial production, logistics | 0.25 |
| Services | Finance, healthcare, education | 0.20 |
| Real Estate | Property development, housing | 0.10 |
| Energy | Power, renewables, utilities | 0.08 |
| Agriculture | Food processing, rural linkages | 0.07 |

---

## Metrics Tracked

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  GDP Delta              ▲ +8.2%                                               │
│  Unemployment Rate      ▼  4.5%                                               │
│  Real Estate Index      ▲  1.12                                               │
│  Transit Congestion     ▲  0.67                                               │
│  Employment Growth      ▲ +5.4%                                               │
│  Capital Formation      ▲ +11.8%                                              │
│  AI Confidence Score    ◆  0.86                                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Testing

```bash
# Backend unit tests
cd backend
pytest tests/unit/ -v

# Backend integration tests
pytest tests/integration/ -v

# Backend load tests
locust -f tests/load/locustfile.py --host http://localhost:8000

# Frontend tests
cd frontend
npm run test

# Lint and type check
npm run lint
npm run type-check
```

```text
┌───────────────────────────────────────────────┐
│ Test Coverage                                 │
├───────────────────────────────────────────────┤
│ Unit Tests        ████████████████████░  90%  │
│ Integration       ███████████████░░░░░  75%  │
│ Load Tests        ██████████░░░░░░░░░░  50%  │
│ Frontend          ████████░░░░░░░░░░░░  40%  │
└───────────────────────────────────────────────┘
```

---

## Deployment

### Backend — Fly.io

```bash
cd backend
fly deploy
```

### Frontend — Vercel

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

```text
Phase 00  Scaffold                  ██████████████████████████  COMPLETE
Phase 01  Simulation Engine          ██████████████████████████  COMPLETE
Phase 02  Backend API Layer          ██████████████████████████  COMPLETE
Phase 03  Frontend Map Shell         ██████████████████████████  COMPLETE
Phase 04  WebSocket Stream           ██████████████████████████  COMPLETE
Phase 05  Controls and Parameters    ██████████████████████████  COMPLETE
Phase 06  RAG + AI Insights          ██████████████████████████  COMPLETE
Phase 07  Loading States             ██████████████████████████  COMPLETE
Phase 08  Polish and UI              ██████████████████████████  COMPLETE
Phase 09  Testing                    ██████████████████████████  COMPLETE
Phase 10  Deployment                 ██████████████████████████  COMPLETE

────────────────────────────────────────────────────────────────────────────

India Overhaul

Phase 00  Data Pipeline              ░░░░░░░░░░░░░░░░░░░░░░░░░░  PLANNED
Phase 01  Engine Rewrite             ░░░░░░░░░░░░░░░░░░░░░░░░░░  PLANNED
Phase 02  Database and API           ░░░░░░░░░░░░░░░░░░░░░░░░░░  PLANNED
Phase 03  Frontend Overhaul          ░░░░░░░░░░░░░░░░░░░░░░░░░░  PLANNED
Phase 04  Performance                ░░░░░░░░░░░░░░░░░░░░░░░░░░  PLANNED
Phase 05  Validation                 ░░░░░░░░░░░░░░░░░░░░░░░░░░  PLANNED
```

---

## Upcoming India Expansion

MetroPulse is planned to expand into a detailed India-first simulation layer.

### Cities

```text
Bengaluru
Mumbai
Delhi NCR
Chennai
Hyderabad
Pune
Kolkata
Ahmedabad
Lucknow
Jaipur
Chandigarh
Bhubaneswar
```

### India-Specific Model Additions

- IT/ITES sector modeling
- Manufacturing corridors
- Informal economy modeling
- Real estate pressure zones
- Public transport stress modeling
- Monsoon and flood risk overlays
- Smart City Mission impact simulation
- AMRUT policy layers
- RERA-linked housing pressure
- PM Awas Yojana affordability effects

---

## Future Vision

```text
[✓] H3 Spatial Simulation Engine
[✓] Real-Time WebSocket Streaming
[✓] RAG + LLM Narrative Layer
[✓] Interactive Policy Sandbox

[ ] Multi-Agent Economic Actors
[ ] Climate Disaster Simulation
[ ] Satellite Data Integration
[ ] Traffic Graph Neural Networks
[ ] Reinforcement Learning Policies
[ ] National Scale Simulation
[ ] Autonomous Urban Planning Agents
```

---

## Contributing

Contributions are welcome.

```text
Fork → Branch → Build → Test → Pull Request
```

### Steps

```bash
git checkout -b feat/amazing-feature
git commit -m "feat(scope): add amazing feature"
git push origin feat/amazing-feature
```

Then open a Pull Request.

---

## Commit Convention

| Prefix | Usage |
|---|---|
| `feat()` | New feature |
| `fix()` | Bug fix |
| `refactor()` | Code refactor |
| `test()` | Tests |
| `docs()` | Documentation |
| `chore()` | Maintenance |

---

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

<div align="center">

```text
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                       METROPULSE                                             ║
║                                                                              ║
║              Where data meets geography,                                     ║
║              where policy meets prediction,                                  ║
║              and where cities become simulatable.                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Built with 💛 for urban futures.

```text
github.com/MrNK2107/MetroPulse
```

</div>
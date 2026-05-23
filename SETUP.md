# MetroPulse — Local Setup Guide

## Prerequisites

- **Python 3.11+** — https://python.org
- **Node.js 20+** — https://nodejs.org
- **Mapbox token** — https://account.mapbox.com (free public token)
- **LLM provider** (optional) — one of: OpenAI key, Google Gemini key, or [Ollama](https://ollama.com) running locally. Fallback works without any.

---

## 1. Backend Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend\.env`:

```env
# LLM Provider: "openai", "gemini", or "ollama"
LLM_PROVIDER=openai
LLM_MODEL=

# OpenAI (used when LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-your-key

# Google Gemini (used when LLM_PROVIDER=gemini)
GEMINI_API_KEY=your-gemini-key

# Ollama (used when LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434

# Embedding provider (defaults to LLM_PROVIDER)
EMBEDDING_PROVIDER=
EMBEDDING_MODEL=

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
WS_MAX_CONNECTIONS=10
SIM_TIMEOUT_MS=3000
LLM_TIMEOUT_MS=10000
```

Start the backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Verify: http://localhost:8000/api/health  
API docs: http://localhost:8000/docs  

Run tests:

```powershell
pytest tests/ --tb=short -v
```

---

## 2. Frontend Setup

```powershell
cd frontend
npm install
npm install --legacy-peer-deps    # if peer dep errors
```

Create `frontend\.env.local`:

```env
NEXT_PUBLIC_MAPBOX_TOKEN=pk.ey...
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/simulate
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the frontend:

```powershell
npm run dev
```

Open http://localhost:3000.

Run checks:

```powershell
npm run lint
npm run type-check
```

---

## 3. Running Full Stack (two terminals)

| Terminal | Command | URL |
|----------|---------|-----|
| 1 (Backend) | `cd backend && .venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload --port 8000` | http://localhost:8000 |
| 2 (Frontend) | `cd frontend && npm run dev` | http://localhost:3000 |

---

## 4. Running a Simulation

1. Move **Technology FDI** slider to **+30%**
2. Select **12m** horizon
3. Click **"Run Simulation"**
4. Hex grid appears with green/amber/red coloring
5. Metric charts populate in real-time
6. AI Insight panel shows analysis (or fallback text)

---

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Map shows blank/gray | `NEXT_PUBLIC_MAPBOX_TOKEN` is missing or invalid |
| WebSocket connection refused | Backend not running on port 8000 |
| `npm install` peer dep errors | Use `npm install --legacy-peer-deps` |
| `pip install h3` fails | Install cmake first or use a pre-built wheel |
| AI Insight shows fallback text | No LLM provider configured. Set `LLM_PROVIDER` + matching API key, or ensure Ollama is running |
| CORS errors | Ensure `CORS_ORIGINS=http://localhost:3000` in backend `.env` |

---

## 6. Quick-Start Script

Save as `start.ps1` in project root:

```powershell
$backend = Start-Process powershell -ArgumentList "-NoExit -Command cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000" -PassThru
$frontend = Start-Process powershell -ArgumentList "-NoExit -Command cd frontend; npm run dev" -PassThru

Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Press any key to stop both..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
$backend.Kill()
$frontend.Kill()
```

# MetroPulse: Local Setup Guide

## Prerequisites

- **Python 3.11+**: https://python.org
- **Node.js 18.17+** (CI uses Node 20): https://nodejs.org
- **LLM provider** (optional, only needed for the agent). One of: a MiMo gateway key (the
  default provider), an OpenAI key, a Google Gemini key, or [Ollama](https://ollama.com) running
  locally. Without one, the map still works, but agent sessions end with a generic `AGENT_ERROR`.
- **No map API key is needed.** The map draws GeoJSON boundaries served by the backend with deck.gl.
  There is no basemap.

---

## 1. Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env
```

Edit `backend\.env`. Every value is optional. The ones that matter most:

```env
# LLM provider: "mimo" (default), "openai", "gemini" or "ollama"
LLM_PROVIDER=ollama
LLM_MODEL=                      # empty = provider default
LLM_TIMEOUT_MS=150000           # small local models are slow; the default is 25000
MIMO_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_NUM_CTX=8192             # context per call; 0 = server default (can be huge)

# Agent socket: disabled while empty
AGENT_WS_TOKEN=pick-a-long-random-string
# Optional: require a token for POST /api/ingest (empty = open, the default)
INGEST_TOKEN=
WS_MAX_CONNECTIONS=10

# Supabase: empty = in-memory fallback
SUPABASE_URL=
SUPABASE_KEY=

# App
CORS_ORIGINS=http://localhost:3000
TWIN_DATA_DIR=                  # empty = data/twin in the repo
```

`backend\.env.example` lists the rest (embedding provider, realtime refresh intervals).

Start the backend:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Check http://localhost:8000/api/health. The API docs are at http://localhost:8000/docs.

At startup the backend fetches Google News RSS and GDELT once for each of the 30 cities, 2 s
apart, then one city every `NEWS_REFRESH_SECONDS`. Offline, these fetches fail and are logged as
warnings. Nothing else depends on them.

Run the tests:

```powershell
python -m pytest tests/unit tests/integration -q
```

---

## 2. Build the twin data (optional)

The map needs a built twin. Without it, the page shows a setup panel listing these same steps.

```powershell
cd backend
python scripts/twin_build.py check
```

Put the 7 files it lists into `data\twin\manual\`. `data\twin\manual\README.md` says where each
one comes from. LGD, Survey of India and VIIRS need a browser login or a captcha. Then run:

```powershell
python scripts/twin_build.py build --boundary-version lgd-YYYYMMDD
```

The running API picks up the new build without a restart.

---

## 3. Frontend setup

```powershell
cd frontend
npm install
```

`frontend\.env.local` is optional. `frontend\.env.example` shows these defaults (copy it to `frontend\.env.local`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/agent
```

An old `/ws/simulate` value is rewritten to `/ws/agent` automatically.

Do not put `AGENT_WS_TOKEN` in `frontend\.env.local`, because anything `NEXT_PUBLIC_*` is shipped to
the browser. The "Ask the agent" panel asks for the token and keeps it in `sessionStorage` only.

Start the frontend:

```powershell
npm run dev
```

Open http://localhost:3000.

Run the checks:

```powershell
npm run test
npm run lint
npm run type-check
```

---

## 4. Full stack (two terminals)

| Terminal | Command | URL |
|----------|---------|-----|
| 1 (Backend) | `cd backend && .venv\Scripts\Activate.ps1 && python -m uvicorn app.main:app --reload --port 8000` | http://localhost:8000 |
| 2 (Frontend) | `cd frontend && npm run dev` | http://localhost:3000 |

## 5. Try it

1. Click a district on the map, or search for one at the top left. The panel lists its
   indicators. Each one has a trust label and a source receipt.
2. Click **Ask the agent** (bottom right), enter the `AGENT_WS_TOKEN` value, and ask something
   like "What happens to Pune if IT FDI rises 30%?". The panel streams the agent's steps
   (`AGENT_THINK`, `AGENT_ACTION`). When the agent asks a question (`AGENT_ASK`), it shows
   buttons for the answers.

---

## 6. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Map shows the "hasn't been built yet" panel | The twin data is not built. Follow section 2, or point `TWIN_DATA_DIR` at a built folder |
| Every request fails with "Failed to fetch" | The backend is not running, or the frontend's origin is not in `CORS_ORIGINS` (needed when the frontend is not on port 3000) |
| Agent panel shows "Disabled" | `AGENT_WS_TOKEN` is empty in `backend\.env`. Set it and restart uvicorn |
| Agent socket closes with 1008 / HTTP 403 | The token typed in the panel does not match `AGENT_WS_TOKEN` |
| Agent replies with a generic AGENT_ERROR | No working LLM provider, or the LLM call hit `LLM_TIMEOUT_MS`. The backend log has the details |
| `/api/health` shows `in_memory_fallback` | Expected without `SUPABASE_URL`/`SUPABASE_KEY` |
| `pip install h3` fails | Install cmake first or use a pre-built wheel |
| spaCy model missing warnings | Run `python -m spacy download en_core_web_sm` in the backend venv |

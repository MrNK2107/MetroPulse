# MetroPulse → India Twin: Design

**Date:** 2026-10-18
**Status:** Draft for owner approval
**Owner:** MrNK2107 (decides) · **Builder:** Claude (builds everything)

Calls marked **[Claude's call]** were made by the builder, not agreed by the owner. They can be overridden.

---

## 1. Intent

Build a clone of **all of India** that anyone can ask **anything**. That covers simple questions like "what's the weather in my area?" and huge ones like "what happens if the US tries to corner India?"

The owner wants the big what-if answers to be **mind-blowing**: every way the future could go, shown as impacts on the map of India and played like a film. The owner also confirmed that every number must be **traceable**. It should look stunning, but nothing is invented. Facts are sourced, and anything guessed is labelled as a guess.

### Why the current MetroPulse falls short

Today MetroPulse simulates one city at a time with hand-set economic formulas. Its numbers can't be checked, it only answers policy-shock questions, and it covers only some cities. The new design turns MetroPulse into a **data twin**: real datasets for the whole country, lined up on one map, plus a map of how places and industries depend on each other, plus a library of what actually happened in past shocks. An AI agent answers questions by querying and reasoning over those three things, not from its own memory.

### Who it's for

There's no single target user (owner's words: "they may ask anything"). It's a general public tool. Questions can come from a student, a journalist, an official, a business owner or a curious citizen.

---

## 2. Goals, non-goals, anti-goals

### Goals
1. **All of India from day one.** Every state and district is covered in the first release, thinly at first, then deeper over time (districts → cities → wards → hexagons).
2. **Ask anything.** Any question in natural language gets the best answer the twin can support.
3. **Mind-blowing what-ifs.** A scenario tree with likelihoods, and each branch plays as a cinematic sequence on the map.
4. **Everything traceable.** Every number on screen carries its source, date and one of three trust labels: **Fact**, **Pattern** or **Projection**.
5. **Cheap to run.** Free public data, open-source tools, and pay-as-you-go AI as the only meaningful running cost.

### Non-goals (for now)
- Real-time precision forecasting, such as tomorrow's stock prices or election results.
- Personal data about individuals. The twin works with aggregates and places, never people.
- Languages other than English (can be added later).
- Mobile-first design. Desktop gets the cinematic experience first, and mobile must work but can be simpler.
- Payments, subscriptions or organisation/team accounts.
- Actually deploying publicly. Everything is built deploy-ready, but going live is the owner's later decision.

### Anti-goals (failure even if it "works")
- **A beautiful lie.** Numbers the AI made up and presented as if they came from data. This is the single worst failure.
- **False precision.** "GDP falls 0.8734%." Projections are always ranges.
- **Propaganda or partisanship.** Geopolitical and political answers must be neutral, show the competing views, and never take sides.
- **A harm playbook.** Questions about how to attack infrastructure, target communities or evade security get declined. The twin describes impacts, never how to cause them.
- **Wrong maps of India.** India's borders must follow the official Survey of India boundary. Showing them wrongly is a legal and reputational problem in India.
- **Silence when the data is missing.** When the twin doesn't know, it says so, names what data would be needed, and still gives whatever partial answer it honestly can.

---

## 3. What the user experiences

### 3.1 Three kinds of answers
Every question is routed to one of three kinds of answer. The kind is shown on screen.

| Kind | Example | How it's answered | Screen |
|---|---|---|---|
| **Lookup** | "Weather in Pune now?", "Population of Gaya district?" | Query a dataset or live feed | Map fly-to, an answer card with source, a small chart if useful |
| **Analysis** | "Which districts improved child nutrition most since 2015?", "Does MGNREGA spending track migration?" | Agent runs queries, comparisons, trends and correlations over the data | Map coloured by result, a ranked list, a chart, a short narrative, and caveats such as "correlation, not cause" |
| **Scenario** | "What if the US tries to corner India?", "What if the monsoon fails two years in a row?" | Scenario builder (§5.6) | The combined tree + cinematic screen (§3.2) |

Mixed questions ("Weather in Chennai and will it flood?") get a lookup answer plus a smaller scenario.

### 3.2 Scenario screen (owner approved the mockup `combined-v1`, saved at `docs/superpowers/specs/assets/2026-10-18-scenario-screen-combined-v1.html`)

**What a branch is [Claude's call]:** each branch is an **alternative future**. Siblings at the same level are mutually exclusive ways things could go, and their likelihoods add up to 100%. Impact kinds (economy, security, diplomacy and so on) are **not** branches. They are layers shown *within* every branch's playback, and the top-bar switches turn them on and off. Propagation runs once per leaf branch. "Switching branches" compares whole alternative futures.

**Numbers vs descriptions per impact kind [Claude's call]:**
- **Economy, jobs, trade, energy and migration:** quantified as ranges, using the graph and elasticities.
- **Security, diplomacy and society:** shown as **qualitative events** on the map and timeline, such as "defence spares delays likely", "EU FTA talks accelerate" or "protests in textile belt". Each is labelled Pattern or Projection with sources, and **has no numbers** unless a real dataset and episode support one.

This keeps the "no invented numbers" rule.

- **Top bar:** the question, plus switches for each kind of impact: Economy, Jobs, Security, Diplomacy, Society, Energy, Environment.
- **Left, scenario tree:** main branches and sub-branches, up to 3 levels deep and about 10–30 leaves. Each branch shows:
  - a likelihood (rounded to 5% and labelled Projection)
  - a confidence meter
  - the past episodes it's based on
- **Centre, cinematic map:** a dark map of India. Press play and the selected branch unfolds:
  - a timeline from Day 0 to years out, with event markers
  - shockwaves pulsing at affected places
  - animated flow lines (exports, migration, money, energy)
  - the camera flying to and zooming into key places
  - zoom-in cards for places like Tiruppur
  - narration captions for each moment
  - play, pause and scrub controls
- **Right, "Why this happens":** a numbered chain of cause and effect. Each step names its source and carries a trust label.
- **Bottom, impact ledger:** headline totals (GDP range, jobs at risk, currency, hardest-hit states). These update as the timeline plays.
- **Switching branches:** click another branch and it plays on the same map, so futures are easy to compare.
- **Streaming:** the tree appears first (within seconds), then each branch fills in as it's computed. The user never stares at a blank screen.

### 3.3 Trust labels everywhere
- **Fact:** a value read directly from a named dataset, with its date.
- **Pattern:** derived from data or past episodes, such as a trend, a correlation or "in 2019 a similar shock did X".
- **Projection:** model output about the future. Always a range, always with a confidence level.

Hover or click any number to see its source, date and how it was calculated.

---

## 4. Constraints

- **The builder is Claude.** The owner decides and reviews, and doesn't write code. So the design favours simple, well-tested components and a small number of moving parts.
- **Zero running cost:**
  - free and open data only
  - open-source software
  - everything runs on the owner's machine; Supabase can be the local Supabase stack or the free tier
  - AI is local (see below)
- **Existing stack is kept:**
  - Backend: FastAPI and Python, with NumPy for computation
  - Frontend: Next.js 14, deck.gl, MapLibre and h3-js
  - Database: Supabase Postgres with pgvector
  - AI: the configurable `LLM_PROVIDER`
- **Map borders:** use the official Survey of India boundary for the outline and for Jammu & Kashmir and Ladakh. District boundaries come from official or LGD-aligned sources.
  - **[Claude's call]:** no third-party basemap that draws borders.
  - The dark basemap is **self-hosted vector tiles** built from an OSM extract (for example Protomaps / PMTiles) with OSM's admin borders removed. All borders are drawn only from our own SoI-aligned boundary layer.
  - District boundaries are clipped to the SoI national outline.
  - The SoI outline itself comes from the SoI's published political map / Bhuvan downloads. M1 starts with a task to obtain and record it in the registry.
- **Built production-complete, tested locally (owner decided).** Everything a public product needs is built and tested now, including login, rate limiting, optimisation and testing. It's only *run* locally until the owner decides to go public.
- **Two AI modes, switched by config (owner decided):**
  - **Local mode (now):** Ollama on the owner's GPU, details below.
  - **Public mode (later):** a cloud AI provider, using an API key the owner will supply.

  Switching is a config change only (`LLM_PROVIDER`, model and key environment variables), with no code changes. The benchmark (§5.7) runs in both modes so quality can be compared.
- **Accounts and login [Claude's call on specifics]:**
  - **Supabase Auth** with email magic link and Google sign-in.
  - **Roles:** `user` and `admin`. The owner is admin.
  - **Anonymous visitors** can browse the map and ask Lookup questions within a small limit.
  - **Analysis and Scenario questions require login**, because they're the expensive ones.
  - **Saved answers and history** belong to each user.
  - **Admin screens:** graph-edge review queue, neutrality review queue, usage and cost dashboard, dataset freshness status, user list with the ability to block. They're protected by the admin role, checked on the server.
- **Rate limiting and cost protection [Claude's call on specifics]:**
  - Per-user and per-IP limits for each answer kind. Defaults: Lookup 60/hour, Analysis 20/hour, Scenario 5/day.
  - A **global daily AI spend cap** in public mode, and a hard limit on AI calls per scenario.
  - When the cap is hit, new uncached scenarios are queued or politely refused. Cached answers and lookups keep working.
  - All limits live in config.
  - In local mode, the same limiter runs with generous defaults so it gets exercised in testing.
- **Safety gate:** a classifier step in the router declines harmful requests (§2 anti-goals) and logs them for admin review. It's active in both modes.
- **Observability:**
  - structured JSON logs with a request ID on every answer
  - each AI call records model, tokens or time, and cache hit
  - an error tracker that is free or self-hosted
  - a health endpoint covering the database, model provider and data freshness
- **Performance targets [Claude's call]:**
  - **Public mode:**
    - Lookup answer under 3 seconds
    - Analysis under 15 seconds
    - first scenario branch visible under 20 seconds
    - full scenario under 2 minutes
  - **Local mode:** slower is fine, with progress always visible.
  - **Map:** a smooth 60 fps during cinematic playback on a mid-range laptop.
  - **Load:** the API holds 50 concurrent users in load tests.
- **Testing throughout:**
  - **Unit tests** for every backend module.
  - **Integration tests** for every API and WebSocket path.
  - **Data pipeline tests:** each dataset's validation is checked against known published totals.
  - **Benchmark and backtest evaluations** (§5.7).
  - **Frontend:** component tests and Playwright end-to-end tests for the main flows (sign in, lookup, analysis, scenario playback, admin review).
  - **Load test** and a security review before launch.
- **Local AI models (owner decided):** in local mode, all AI runs on the owner's **RTX 5060 with 8 GB VRAM**, through Ollama, using the existing `LLM_PROVIDER=ollama` path. What follows from this **[Claude's call]**:
  - **Model size:**
    - chat and agent work use a model of about 7–9B parameters at 4-bit quantisation (Qwen3 8B or Llama 3.1 8B class)
    - routing uses a smaller model (about 1–4B)
    - the builder picks the exact models by running the benchmark (§5.7)
  - **Embeddings:** a local embedding model (nomic-embed-text or bge-m3 class). The vector column size changes from 1536 to match it (a new migration).
  - **Code does the heavy lifting:** small models are weaker at long reasoning and tool use. So the design leans harder on deterministic code:
    - every AI call asks for **JSON in a fixed schema**, which is validated and retried on failure
    - prompts are short and single-purpose
    - tree framing, branch generation and narration are separate small calls instead of one big one
    - all numbers come from the engine, never from the model
  - **Speed:** expect a fresh scenario to take a few minutes on this GPU. Streaming (§5.6 step 7) shows progress live, and cached replays are instant.
  - **One model at a time:** with 8 GB VRAM, only one chat model is loaded at a time. Calls go through a single-worker queue so they don't fight for the GPU.
- **Old simulator [Claude's call]:**
  - the new twin **replaces the city simulator in place**, with no parallel running
  - before work starts, the current state is tagged in git (`legacy-metropulse`) so nothing is lost
- **Uncommitted work [Claude's call]:**
  - before M1, the whole current working tree is committed to a branch `wip/swarm-and-agent` as a snapshot
  - main then takes only the keepers: `app/data_registry.py`, `app/source_ingestion.py`, `engine/agent/`, `app/simulation/llm.py`, the `llm_fn` changes in `prediction_generator.py` / `config.py`, and the `dataset_versions` parts of migration 008
  - the swarm, the pixel UI and the run/project routes stay on the branch
- **Data licences:** respect every source's terms. The existing `SOURCE_REGISTRY` already records each licence, and that continues. No scraping of portals that forbid it.
- **Existing conventions:** follow AGENTS.md:
  - the `{success, data, error, meta}` response envelope
  - engine code never imports from the app layer (dependencies are passed in)
  - no database writes mid-simulation
  - commit format `type(scope): description`

---

## 5. Architecture

Five parts, built in this order:

```
 ┌───────────────────────────┐   ┌───────────────────────────┐   ┌──────────────────────────┐
 │ 1. Spatial backbone       │──▶│ 2. Data clone             │──▶│ 3. Connections graph     │
 │ LGD codes, boundaries,    │   │ versioned datasets, all   │   │ who depends on whom      │
 │ H3 grid, crosswalks       │   │ aligned to the backbone   │   │ (trade, migration, …)    │
 └───────────────────────────┘   └───────────────────────────┘   └──────────────────────────┘
                                                │                             │
                                                ▼                             ▼
                                ┌───────────────────────────┐   ┌──────────────────────────┐
                                │ 5. Answer engine           │◀──│ 4. Episodes library      │
                                │ router · tools · scenario │   │ what actually happened   │
                                │ builder · trust checker   │   │ after past shocks        │
                                └─────────────┬─────────────┘   └──────────────────────────┘
                                              ▼
                                ┌───────────────────────────┐
                                │ 6. Experience (frontend)  │
                                └───────────────────────────┘
```

### 5.1 Spatial backbone
Everything in the twin attaches to a place in one shared system.

- **Place IDs:** use **LGD codes** (Local Government Directory, the government's official place codes). The levels are:
  - country
  - state or union territory
  - district
  - sub-district (tehsil or taluk)
  - block
  - town or village
  - urban local body
  - ward, where available
- **Boundary versions over time:** India has gone from 640 districts in 2011 to over 780 today. Keep a **crosswalk table** that maps old district codes to new ones with area and population weights. That way Census 2011 data can be shown on today's districts and vice versa. Every dataset records which boundary version it uses.
- **Name matching:** an aliases table ("Gurgaon" = "Gurugram", spelling variants, Hindi and English names) is used whenever data is loaded.
- **H3 hexagon grid** for data that comes as satellite pixels or points, such as nightlights, population grids, weather grids and facility locations:
  - resolution 5 nationally
  - resolution 7 for districts
  - resolution 8–9 for cities, as depth is added

  Each hexagon is linked to the district or town it falls in, so data can roll up and down between hexagons and places.
- **Storage [Claude's call]:**
  - PostGIS in Supabase for boundaries and place tables
  - big gridded data kept as **Parquet files queried with DuckDB** (free, fast, no server cost)
  - only summarised results loaded into Postgres

### 5.2 Data clone
Builds on the existing `app/data_registry.py` (`SOURCE_REGISTRY`, `dataset_versions` table) and `app/source_ingestion.py`.

**Pipeline for every dataset:**
1. **Fetch.** Download or call the API, then save an untouched copy (`raw/<source>/<version>/`) with its checksum.
2. **Parse.** Turn PDF, Excel, CSV or raster files into tidy tables.
3. **Align.** Match every row to LGD codes or H3 hexagons, using the aliases table and the boundary crosswalk.
4. **Validate.** Check totals against published totals, check ranges, and flag missing districts. If validation fails, the version isn't published.
5. **Publish.** Release a versioned table with the data's observation date, source, licence and trust class.

**One shape for every value [Claude's call]:**

`indicator, place_id (LGD or H3), period, value, unit, source_id, dataset_version, trust_class`

plus an **indicator catalogue** (name, description, unit, which domains it belongs to). The agent searches this catalogue to find what data exists for a question.

**First release, all districts (~20 sources)** [Claude's call on the exact list; the builder may swap equivalents]:

| Domain | Sources |
|---|---|
| Places | LGD directory, Survey of India / official district boundaries |
| People | Census 2011 PCA and migration D-series, NFHS-5 district factsheets, WorldPop / GHSL population grids |
| Work and economy | PLFS (state), VIIRS nightlights (district totals, as an activity proxy), state GDP (MoSPI), DGFT "Districts as Export Hubs" / district export data, MCA company registry counts |
| Trade | DGCI&S / Commerce Ministry trade by commodity and partner country |
| Infrastructure | OpenStreetMap (roads, rail, hospitals, schools, ports, power plants) |
| Environment | IMD rainfall and temperature, CPCB air quality |
| Governance | Election Commission results (assembly and parliament constituencies, mapped to districts), MGNREGA district data |
| Live | Open-Meteo or IMD weather, CPCB live air quality, GDELT / news (context only) |

**Getting deeper later:** add city-level layers (ward boundaries, GTFS transit, municipal budgets), then H3 resolution 8–9 detail for the top cities. The existing 30 city YAMLs become city-depth packs.

### 5.3 Connections graph (how India is wired)
A graph of dependencies stored as two plain Postgres tables, `nodes` and `edges`. No graph database is needed.

- **Node types:** place (LGD), sector, commodity, industry cluster (such as "Tiruppur knitwear"), country, infrastructure asset (port, refinery, pipeline, rail corridor), institution (RBI, a central ministry).
- **Edge types**, each with a weight, unit, source, year and trust label:

  | Edge | Example | Where the weight comes from |
  |---|---|---|
  | `exports_to` | Tamil Nadu knitwear → USA | trade data |
  | `imports_from` | India crude oil ← Russia | PPAC and trade data |
  | `supplies` | sector → sector | MoSPI supply-use / input-output tables |
  | `employs` | cluster → district workers | Census, PLFS, cluster studies |
  | `migrates_to` | Bihar districts → Surat, Tiruppur | Census D-series |
  | `remits_to` | migrant destination → origin district | derived from migration; labelled Pattern |
  | `ships_via` | cluster → port | port and export data |
  | `depends_on` | defence platform → foreign supplier | public reports; labelled Pattern, coarse only |

- **How it's built:** from datasets where possible. For gaps, the agent may propose edges from documents (the ingestion pipeline, using RAG over reports). Every proposed edge must cite the passage it came from and is stored as Pattern, never Fact. Edges proposed by the agent are flagged for owner review in an admin list before they affect scenarios.

### 5.4 Episodes library (what actually happened)
Structured records of past shocks to India. They're used to suggest branches, estimate likelihoods, and set how big and how delayed effects are.

- **Each episode records:**
  - the trigger and dates
  - the shock type (tariff, sanctions, oil price, monsoon failure, pandemic, policy, conflict, financial)
  - the nodes affected
  - the observed outcomes as time series, for example "textile exports −X% over 6 months, rupee moved Y"
  - the lag from shock to effect
  - sources
- **Starting set (~25) [Claude's call]:**
  - 1991 balance-of-payments crisis
  - 1998 Pokhran sanctions
  - 2008 global financial crisis
  - 2013 taper tantrum
  - 2016 demonetisation
  - 2017 GST rollout
  - 2019 US GSP withdrawal
  - 2020 COVID lockdown and migrant exodus
  - 2020 China app bans and investment curbs
  - 2022 Russian oil and Ukraine price shock
  - 2023 rice export ban
  - 2025 US tariffs on India
  - major droughts and monsoon failures (2002, 2009, 2014–15)
  - Chennai 2015 and Kerala 2018 floods
  - plus others the builder finds well documented
- **What it produces:**
  - **Elasticities with ranges**, such as "a tariff of X on a labour-heavy export cuts volume by A–B% within C–D months", used by the propagation engine
  - **Base rates**, such as "after US trade pressure, India retaliated in N of M episodes", used for branch likelihoods

### 5.5 Answer engine: router and tools
Grows out of the existing `engine/agent/` ReAct agent.

- **Router:** sorts each question into Lookup, Analysis, Scenario or mixed. A cheap model handles this, with simple rules for obvious cases.
- **Tools the agent can call** (all deterministic, all return results with sources attached):
  - `search_indicators(query)`: search the indicator catalogue for what data exists
  - `resolve_place(text)`: find the LGD code or H3 cell, handling aliases and fuzzy matches
  - `query_data(indicator, places, period, aggregate)`: runs SQL or DuckDB
  - `compare / rank / trend / correlate`: statistics helpers that return numbers plus caveats
  - `graph_neighbours(node, edge_types, depth)`: explore the connections graph
  - `find_episodes(shock_description)`: find similar past episodes
  - `live(kind, place)`: weather, air quality, news
  - `search_documents(query)`: RAG over ingested reports and policy documents, for context only
  - `run_scenario(spec)`: hand off to §5.6
- **Hard rule:** the agent may **never write a number in its answer that didn't come back from a tool.** The trust checker (§5.7) enforces this.

### 5.6 Scenario builder
Turns a what-if question into the tree, the timelines and the narration.

1. **Frame the shock.** The AI turns the question into structured shocks. For example, "US tariffs of 25–50% on Indian goods" lists who is acting, which levers they pull, which nodes are hit first, and a range for the size.
2. **Find analogs.** `find_episodes` returns similar past episodes with their elasticities and base rates.
3. **Generate branches.** The AI proposes branches across all impact kinds (economic, security, diplomatic, social, energy, environment), grounded in the analogs and graph exposures. Then:
   - duplicates are removed
   - the tree is capped at depth 3 and about 30 leaves
   - each branch gets a short, testable description and the levers it changes
4. **Estimate likelihood.** Start from analog base rates, then let the AI adjust with a written reason. Likelihoods are normalised within each level, rounded to 5%, and labelled Projection with confidence high, medium or low. Confidence depends on how many analogs exist and how similar they are.
5. **Propagate.** A deterministic engine, built with the existing NumPy-vectorised style, runs month by month over the connections graph:
   - each affected node's change = the sum over incoming edges of (exposure share × upstream shock × elasticity), applied after the edge's lag, and damped over time
   - uncertainty: about 200 Monte Carlo runs sample the uncertain elasticities and shock sizes, giving a low, middle and high value for every output
   - output: per-month values per node and per place for each impact kind, rolled up to district and state
6. **Write the story.** The AI turns the propagation output into:
   - **keyframes**: time, places to highlight, flows to animate, where the camera goes, a caption
   - the **"why" chain**, with each step linked to the edges, data and episodes behind it
   - **ledger totals**

   The AI may only use numbers that appear in the propagation output.
7. **Stream.** The tree is sent first, then each branch's keyframes as they're ready, over a WebSocket (reusing the patterns in `app/ws/`).
8. **Cache.** Scenario results are stored by their normalised shock spec and data version. A repeat question replays from cache at no AI cost.

**Scenario result format [Claude's call; details left to the builder]:**

```
Scenario { id, question, shock_spec, data_version, created_at,
  tree: Branch[] }
Branch { id, parent_id, title, description, likelihood, confidence, analog_episode_ids,
  timeline: Keyframe[], why_chain: WhyStep[], ledger: LedgerItem[] }
Keyframe { t_month, caption, camera {center, zoom, pitch, bearing},
  highlights [{place_id, metric, low, mid, high}], flows [{from, to, kind, magnitude}] }
WhyStep { order, text, trust_label, source_refs[] }
```

### 5.7 Trust layer
- **Number checker:** before any answer is sent, every number in the text is matched against the tool and engine outputs for that answer. If a number can't be matched, it's removed or the answer is regenerated. Unmatched numbers never reach the user.
- **Source receipts:** every value carries `source_id`, `dataset_version`, its observation date and its trust label. The frontend shows these when a number is hovered or clicked.
- **Honest gaps:** when data is missing, the answer says "no data for X", names which dataset would fill the gap, and still gives whatever the twin can.
- **Safety:** questions asking how to cause harm (attack infrastructure, target groups, evade law enforcement) are declined. Security and defence answers stay at the level of public, high-level information.
- **Evaluations:**
  - **Fact and analysis benchmark:** about 300 questions with known correct answers, drawn from official publications. Run on every change, with accuracy tracked over time.
  - **Scenario backtests:** run the engine "as of" just before a past episode, with that episode removed from the library, and compare the projection to what actually happened. Start with 2019 GSP, 2020 lockdown migration and the 2023 rice ban. Report hit rate (was reality inside the range?) and error.
  - **Neutrality check:** a fixed set of political and geopolitical questions, reviewed for one-sidedness.

### 5.8 Experience (frontend)
- Keep Next.js 14, deck.gl, MapLibre and Zustand.
- **Home:** a single "Ask India anything" box over a dark, live map of India showing current weather and air-quality layers, so the map feels alive before anyone asks a question.
- **Lookup and analysis view:** the map fly-to and colouring, an answer card, a chart, source receipts and caveats.
- **Scenario view:** exactly the approved `combined-v1` layout (§3.2). Cinematic effects use:
  - `ArcLayer` and `TripsLayer` for animated flows
  - pulsing `ScatterplotLayer` rings for shockwaves
  - `GeoJsonLayer` districts or `H3HexagonLayer` cells coloured by impact
  - deck.gl `FlyToInterpolator` for camera moves between keyframes
  - captions synced to the timeline, with play, pause and scrub
- **Follow-up questions** stay in context ("what about Gujarat specifically?").
- **Shareable link** for any answer or scenario, replayed from cache.
- **Account area:** sign in, history of past questions, saved scenarios.
- **Admin area** (admin role only): edge review, neutrality review, usage and cost, data freshness, users.
- **Desktop first.** On mobile, the tree collapses into a drawer and the map stays full-screen.

### 5.9 Live layer
Small scheduled jobs refresh:
- weather (hourly)
- air quality (hourly)
- news signals (every 15 minutes, context only)
- slow datasets (on their release schedule)

Freshness rules (`freshness_sla_days`) already exist in the registry. Answers show "as of" times.

---

## 6. What happens to the existing code

| Existing piece | Fate |
|---|---|
| `app/data_registry.py`, `dataset_versions`, `source_ingestion.py` | **Keep and grow.** These become the data clone pipeline. |
| `engine/agent/` (ReAct agent, tools, memory) | **Keep and grow.** It becomes the answer engine (§5.5). |
| H3 utilities in `engine/grid.py` | **Keep**, widened to national use. |
| RAG (`app/rag/`), case studies | **Keep.** Case studies feed the episodes library and document search. |
| WebSocket streaming (`app/ws/`), `lib/ws.ts`, Zustand stores | **Keep and adapt** for answer and scenario streaming. |
| Map components (`MapViewport`, `HexLayer`, color scales) | **Keep and extend** for the cinematic scenario view. |
| `LLM_PROVIDER` multi-provider support, `llm_fn` dependency injection | **Keep.** |
| City-only loops (`primary_loop`, `secondary_loop`, `tertiary_loop`, `runner.py`, per-city sector coefficients) | **Retire.** Replaced by the graph propagation engine. Keep useful bits (monsoon and flood logic) as optional city-depth tools. |
| `engine/swarm/` (LLM citizen swarm) and `components/pixel/` (uncommitted) | **Park.** Not part of this design. Leave the code in a branch, out of the main path. |
| 30 city YAMLs and GeoJSONs | **Convert** into city-depth packs later. Their invented baselines don't count as Facts. |
| Existing tests | Keep those for retained modules and delete those for retired modules. |

---

## 7. Build order (milestones)
Each milestone ends with something the owner can try. The detailed plan comes next (writing-plans).

1. **M1: Backbone.** LGD places, official boundaries, the district crosswalk, aliases, H3 linking, and the dataset pipeline with 3 sources (LGD, Census 2011 PCA, VIIRS).
   *Demo: "What's the population of Gaya district?" returns a sourced answer on the map.*
2. **M2: Ask anything (facts and analysis).**
   - about 20 sources, the indicator catalogue, router and agent tools, the number checker
   - the lookup and analysis view, live weather and air quality
   - **login, roles, rate limiting, the safety gate, request logging**
   - benchmark v1 (about 100 questions), run in local mode
   *Demo: lookups and comparisons across all districts with receipts.*
3. **M3: Wiring.** The connections graph (trade, input-output, migration, export clusters, energy imports), the episodes library (about 25 episodes with elasticities), and an admin review list for edges proposed by the agent.
   *Demo: "What depends on US demand?" shows a graph explorer on the map.*
4. **M4: Scenario engine.** Shock framing, branch generation, likelihoods, Monte Carlo propagation, keyframe and narration writing, caching, streaming, and the first 3 backtests.
   *Demo: the US question produces a full tree with data (simple view).*
5. **M5: Cinematic.** The full `combined-v1` scenario screen with animated playback, camera moves, why chain, ledger, branch switching and share links.
   *Demo: the mind-blowing version.*
6. **M6: Depth and polish.** City-depth packs for the top cities, more datasets, benchmark expanded to 300, neutrality evaluations, performance tuning against the §4 targets, mobile layout, and the admin dashboards completed.
7. **M7: Launch-ready (still local).**
   - Run the full benchmark and backtests in public mode using a cloud key. Until the owner supplies one, this step is skipped and reported, not faked.
   - Load test to 50 concurrent users.
   - Security review: auth, admin routes, rate limits, injection via ingested documents.
   - Deployment configs updated and dry-run (Fly.io and Vercel, which already exist).
   - A go-live runbook.

   *Demo: flip one config switch and the whole app runs on a cloud model with all limits active.*

---

## 8. Left to the builder
- Exact libraries for PDF and Excel parsing and raster processing.
- Database table layouts beyond the shapes given here.
- Which AI model each task uses (within budget), prompt wording, and caching details.
- Swapping a listed dataset for an equivalent one when a source is unavailable or its licence forbids use, recorded in the registry.
- The visual design details of the cinematic view, within the approved layout.
- Hosting choice within the stated budget, and how jobs are scheduled.

## 9. Calls Claude made (please check)
1. Free data and open source only. AI runs locally for now, and a cloud key comes later (owner decided).
2. DuckDB and Parquet for big gridded data, Postgres and PostGIS for places and summaries.
3. One shared format for every value, plus an indicator catalogue.
4. The starting list of ~20 datasets and ~25 episodes.
5. Likelihoods shown as percentages rounded to 5% and labelled Projection.
6. The citizen swarm and pixel UI are parked, and the city-only economic loops retired.
7. English only and desktop first for the first release.
8. Edges proposed by the agent need owner review before they affect scenarios.
9. Branches are alternative futures. Impact kinds are layers within each branch (§3.2).
10. Security, diplomacy and society are shown as qualitative events, without numbers (§3.2).
11. A self-hosted basemap with only SoI-aligned borders (§4).
12. Local-model specifics: 7–9B chat model, a small router model, local embeddings with a new vector size, fixed-schema JSON calls, and a single-worker GPU queue (§4).
13. The new twin replaces the old simulator in place, with the old state tagged `legacy-metropulse` (§4).
14. Uncommitted work is snapshotted to `wip/swarm-and-agent`, and only the keepers come to main (§4).
15. Supabase Auth with magic link and Google, `user` and `admin` roles, and anonymous visitors limited to Lookups (§4).
16. Default rate limits (Lookup 60/hour, Analysis 20/hour, Scenario 5/day) and the performance targets (§4).
17. A new M7 "launch-ready" milestone (§7).

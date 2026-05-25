# Natural Language Economic Simulation — Design Spec

**Date:** 2026-05-28
**Status:** Approved
**Approach:** C — Hybrid Pipeline with Intent Router

---

## Problem

People (students, policymakers, small businesses) see economic news — fuel price hikes, rainfall drops, interest rate changes — but cannot understand how those changes ripple through society. MetroPulse needs a natural language interface where anyone can describe a "what if?" scenario and watch the cascading effects unfold.

## Goals

1. **Accessible**: Works for users with zero economic knowledge ("what if it floods in Mumbai?")
2. **Precise**: Supports power users who talk numbers ("manufacturing -23%, SEZ policy, Chennai, 36 months")
3. **Cost-efficient**: Minimize LLM API calls — use local models (spaCy, Ollama) for parsing
4. **Conversational**: "What if?" tone, not interrogative. Two modes: Quick and Deep
5. **Human-centered output**: Show impacts on social groups (farmers, students, businesses), not just hex metrics

## Non-Goals

- Modifying the core simulation engine (it stays deterministic NumPy)
- Training custom ML models
- Supporting non-English input (English only for now)
- Real-time multi-turn debates with the LLM

---

## Architecture Overview

```
User Input (NL text)
       │
  Intent Router (<5ms)
       │
  ┌────┼────────┐
  │    │        │
Path1 Path2  Path3
regex spacy  ollama
  │    │        │
  └────┼────────┘
       │
  ParsedScenario (unified)
       │
  Conversation Manager
  (Quick / Deep mode)
       │
  Simulation Engine (unchanged)
       │
  Social Group Scorer
       │
  Evidence + Group Impact Cards
```

---

## Module Structure

```
backend/engine/nl_engine/
├── __init__.py
├── router.py          # Intent router (3-path dispatch)
├── regex_parser.py    # Path 1: enhanced regex
├── spacy_parser.py    # Path 2: spaCy NER + domain knowledge
├── ollama_parser.py   # Path 3: local LLM fallback
├── domain_maps.py     # Synonym maps, cause-effect chains, group definitions
├── conversation.py    # Conversation state machine
└── group_scorer.py    # Post-sim social group impact scoring
```

---

## Intent Router (`router.py`)

The router dispatches input to the cheapest parser that can handle it.

```python
async def route_input(text: str, city_config: dict | None = None) -> tuple[ParsedScenario, float]:
    """Returns (parsed_scenario, confidence_score)"""

    # Path 1: Try regex first (structured inputs with explicit numbers/keywords)
    regex_result = regex_parser.parse(text)
    if regex_result.confidence > 0.8:
        return regex_result, 1.0

    # Path 2: Try spaCy (moderate natural language)
    spacy_result = spacy_parser.parse(text)
    if spacy_result.confidence > 0.6:
        return spacy_result, spacy_result.confidence

    # Path 3: Ollama fallback (complex/ambiguous)
    ollama_result = await ollama_parser.parse(text)
    return ollama_result, ollama_result.confidence
```

**Confidence scoring:**
- Regex: 1.0 if city + at least one sector/delta found, else 0.0
- spaCy: weighted sum of entity match scores (city=0.3, sectors=0.4, delta=0.2, sentiment=0.1)
- Ollama: always returns 0.9 (trust the LLM)

---

## Path 1: Enhanced Regex (`regex_parser.py`)

Upgraded version of the existing `scenario_parser.py`. Changes:

1. **Expanded city aliases** (30+ entries, including neighborhoods like "Bandra" → Mumbai)
2. **Synonym-aware sector matching** via `domain_maps.SECTOR_SYNONYMS`
3. **Cause-effect keyword detection** via `domain_maps.CAUSE_EFFECT_CHAINS`
4. **Better delta extraction**: handles "+15%", "increased by 15%", "15% hike", "went up fifteen percent"
5. **Confidence scoring**: explicit return of how much the parser could extract

---

## Path 2: spaCy Parser (`spacy_parser.py`)

Uses `en_core_web_sm` (~12MB) for entity extraction and dependency parsing.

**Extraction pipeline:**

1. **City detection**: GPE entities matched against known city list with fuzzy matching (Levenshtein distance ≤ 2)
2. **Sector detection**: Noun phrases matched against `SECTOR_SYNONYMS` (e.g., "petrol prices" → transport_logistics)
3. **Delta extraction**: NUM entities + surrounding context ("increased by 15%" → +15%)
4. **Event detection**: Verb + noun patterns matched against `CAUSE_EFFECT_CHAINS` (e.g., "floods hit" → heavy_rainfall event)
5. **Magnitude inference**: If no explicit number, use sentiment-bearing adjectives:
   - "skyrocketed", "crashed", "devastating" → ±40%
   - "significant", "major", "sharp" → ±25%
   - "slight", "minor", "gradual" → ±10%
   - Default: ±15%

**Confidence calculation:**
```python
confidence = 0.0
if city_found: confidence += 0.3
if sectors_found: confidence += 0.4 * (n_sectors / max_expected)
if delta_found: confidence += 0.2
if sentiment_found: confidence += 0.1
```

---

## Path 3: Ollama Parser (`ollama_parser.py`)

Falls back to a local Ollama model (phi-2, tinyllama, or llama3.2:3b) when spaCy confidence is low. **If Ollama is not installed/running**, returns the spaCy result with a warning that parsing may be inaccurate. This makes Ollama fully optional.

**Prompt template:**
```
You are an economic scenario parser. Given a user's text, extract structured parameters.

User text: "{text}"

Extract as JSON:
{
  "city": "city name or null",
  "sectors": [
    {"name": "sector_name", "delta": number, "direction": "up|down"}
  ],
  "policies": ["policy_name"],
  "events": ["event_name"],
  "horizon_months": number,
  "confidence": number (0-1)
}

Valid sectors: it_ites, manufacturing, real_estate, trade_hospitality, transport_logistics, informal, public_admin
Valid policies: sez, smart_city, amrut, rera, pm_awas, make_in_india, digital_india
Valid events: fuel_price_hike, heavy_rainfall, drought, interest_rate_hike, subsidy_added, unemployment_rise, pandemic

Respond with only the JSON object.
```

**Post-processing:** Validates extracted JSON against known schemas, applies domain_maps for any remaining fuzzy matches, caps deltas at ±50%.

---

## Domain Maps (`domain_maps.py`)

The knowledge backbone that all three paths share.

### Sector Synonyms (50+ entries)

```python
SECTOR_SYNONYMS = {
    # Transport & fuel
    "petrol": "transport_logistics", "diesel": "transport_logistics",
    "fuel": "transport_logistics", "gas": "transport_logistics",
    "uber": "transport_logistics", "ola": "transport_logistics",
    "auto": "transport_logistics", "truck": "transport_logistics",
    "bus": "transport_logistics", "metro": "transport_logistics",

    # IT & tech
    "tech": "it_ites", "software": "it_ites", "startup": "it_ites",
    "it": "it_ites", "digital": "it_ites", "ai": "it_ites",
    "coding": "it_ites", "wfh": "it_ites", "outsourcing": "it_ites",

    # Manufacturing
    "factory": "manufacturing", "industrial": "manufacturing",
    "electricity": "manufacturing", "power": "manufacturing",
    "steel": "manufacturing", "cement": "manufacturing",

    # Agriculture & informal
    "crop": "informal", "farm": "informal", "harvest": "informal",
    "monsoon": "informal", "rain": "informal", "drought": "informal",
    "agriculture": "informal", "village": "informal",

    # Real estate
    "rent": "real_estate", "housing": "real_estate", "flat": "real_estate",
    "construction": "real_estate", "property": "real_estate",

    # Trade & hospitality
    "shop": "trade_hospitality", "restaurant": "trade_hospitality",
    "mall": "trade_hospitality", "tourism": "trade_hospitality",
    "hotel": "trade_hospitality", "market": "trade_hospitality",

    # Public admin
    "government": "public_admin", "govt": "public_admin",
    "subsidy": "public_admin", "tax": "public_admin", "budget": "public_admin",
}
```

### Cause-Effect Chains (15+ events)

```python
CAUSE_EFFECT_CHAINS = {
    "fuel_price_hike": {
        "transport_logistics": +0.20,
        "manufacturing": -0.08,
        "trade_hospitality": -0.05,
        "informal": -0.10,
    },
    "heavy_rainfall": {
        "informal": -0.25,
        "transport_logistics": -0.15,
        "real_estate": -0.08,
        "trade_hospitality": -0.10,
    },
    "interest_rate_hike": {
        "real_estate": -0.15,
        "manufacturing": -0.08,
        "it_ites": -0.05,
        "trade_hospitality": -0.06,
    },
    "subsidy_added": {
        "informal": +0.12,
        "trade_hospitality": +0.06,
        "manufacturing": +0.04,
    },
    "unemployment_rise": {
        "it_ites": -0.10,
        "manufacturing": -0.12,
        "trade_hospitality": -0.08,
        "real_estate": -0.06,
    },
    "drought": {
        "informal": -0.35,
        "trade_hospitality": -0.10,
        "manufacturing": -0.05,
    },
    "tech_boom": {
        "it_ites": +0.30,
        "real_estate": +0.15,
        "trade_hospitality": +0.10,
    },
    # ... more events
}
```

### Social Group Definitions

```python
SOCIAL_GROUPS = {
    "farmers": {
        "income_sectors": ["informal"],
        "expense_sectors": ["transport_logistics", "manufacturing"],
        "sensitivity": {"rainfall": 0.8, "fuel": 0.6, "subsidy": 0.7, "drought": 0.9},
        "population_weight": 0.42,  # 42% of workforce
    },
    "students": {
        "income_sectors": ["it_ites"],
        "expense_sectors": ["real_estate", "trade_hospitality"],
        "sensitivity": {"interest_rate": 0.5, "unemployment": 0.7, "tech": 0.6},
        "population_weight": 0.08,
    },
    "middle_class_families": {
        "income_sectors": ["it_ites", "manufacturing", "public_admin"],
        "expense_sectors": ["real_estate", "trade_hospitality", "transport_logistics"],
        "sensitivity": {"inflation": 0.7, "interest_rate": 0.6, "fuel": 0.5},
        "population_weight": 0.25,
    },
    "small_businesses": {
        "income_sectors": ["trade_hospitality", "manufacturing"],
        "expense_sectors": ["transport_logistics", "real_estate"],
        "sensitivity": {"fuel": 0.6, "demand": 0.7, "interest_rate": 0.5},
        "population_weight": 0.10,
    },
    "corporates": {
        "income_sectors": ["it_ites", "manufacturing", "trade_hospitality"],
        "expense_sectors": ["transport_logistics"],
        "sensitivity": {"policy": 0.6, "global": 0.5, "interest_rate": 0.4},
        "population_weight": 0.03,
    },
    "transport_sector": {
        "income_sectors": ["transport_logistics"],
        "expense_sectors": ["manufacturing"],  # fuel costs
        "sensitivity": {"fuel": 0.9, "demand": 0.6, "rainfall": 0.4},
        "population_weight": 0.07,
    },
    "government": {
        "income_sectors": ["public_admin"],
        "expense_sectors": ["informal", "manufacturing"],
        "sensitivity": {"subsidy": 0.8, "tax": 0.7, "unemployment": 0.6},
        "population_weight": 0.05,
    },
}
```

---

## Conversation Manager (`conversation.py`)

### Mode Detection

```python
def detect_mode(text: str, parsed: ParsedScenario) -> str:
    """Returns 'quick' or 'deep' mode."""
    # Deep mode indicators
    has_numbers = bool(re.search(r'\d+%?', text))
    has_explicit_params = parsed.sectors and parsed.city and parsed.horizon_months
    has_mode_keywords = any(w in text.lower() for w in ["deep mode", "talk numbers", "precise"])

    if has_numbers or has_explicit_params or has_mode_keywords:
        return "deep"

    # Quick mode indicators
    has_vague_language = any(w in text.lower() for w in [
        "what if", "imagine", "suppose", "happens", "affect", "impact"
    ])
    if has_vague_language or not has_explicit_params:
        return "quick"

    return "quick"  # default
```

### Conversation State Machine

```
States: IDLE → PARSING → [NEEDS_INPUT → PARSING] → CONFIRMED → SIMULATING → DONE

Transitions:
- IDLE → PARSING: user sends scenario text
- PARSING → CONFIRMED: high confidence, all params extracted
- PARSING → NEEDS_INPUT: low confidence or missing critical params
- NEEDS_INPUT → PARSING: user responds to follow-up
- CONFIRMED → SIMULATING: user confirms params
- SIMULATING → DONE: simulation complete
```

### Follow-up Questions

Quick mode generates targeted follow-ups based on what's missing:

```python
FOLLOW_UP_TEMPLATES = {
    "missing_city": "Which city are you thinking about?",
    "missing_severity": "How big should this shock be — mild, moderate, or severe?",
    "missing_sector": "Which part of the economy should I focus on?",
    "ambiguous_event": "I detected {event}. Which sectors do you think get hit hardest?",
    "missing_horizon": "How far out should I simulate — 6 months, a year, or 2 years?",
}
```

Deep mode skips follow-ups — if params are explicit, confirm and run.

---

## WebSocket Protocol Changes

### New Message Types

**Server → Client: NEEDS_INPUT**
```json
{
  "type": "NEEDS_INPUT",
  "question": "How severe — mild, moderate, or catastrophic?",
  "inferred_params": {
    "city": "mumbai",
    "sectors": [{"name": "transport_logistics", "delta": 20}],
    "events": ["fuel_price_hike"]
  },
  "options": ["Mild", "Moderate", "Severe"],
  "mode": "quick"
}
```

**Client → Server: INPUT_RESPONSE**
```json
{
  "type": "INPUT_RESPONSE",
  "text": "Severe"
}
```

**Server → Client: GROUP_SCORES**
```json
{
  "type": "GROUP_SCORES",
  "groups": [
    {
      "name": "farmers",
      "purchasing_power": -18,
      "income_stability": -22,
      "expense_pressure": +12,
      "housing_impact": -5,
      "employment_impact": -8,
      "severity": "high"
    }
  ],
  "citizen_satisfaction": 34
}
```

### Updated Pipeline Flow

```
START → STAGE(parsing) → [NEEDS_INPUT → INPUT_RESPONSE → STAGE(parsing)] →
PARSED → STAGE(predicting) → PREDICTION → STAGE(simulating) →
FRAME... → STAGE(retrieving) → CASE_STUDIES →
STAGE(synthesizing) → GROUP_SCORES → EVIDENCE → DONE
```

---

## Social Group Scorer (`group_scorer.py`)

Post-simulation scoring that derives group impacts from existing simulation data.

```python
def score_groups(sim_frames: list[SimulationFrame], city_config: dict) -> list[GroupImpact]:
    """Compute per-group impacts from final simulation state."""
    final = sim_frames[-1]

    results = []
    for group_name, group_def in SOCIAL_GROUPS.items():
        # Income: weighted average of income sector deltas
        income_delta = weighted_avg(
            [get_sector_delta(final, s) for s in group_def["income_sectors"]],
            [group_def["sensitivity"].get(s, 0.5) for s in group_def["income_sectors"]]
        )

        # Expenses: weighted average of expense sector deltas (inverted — costs go up = bad)
        expense_delta = weighted_avg(
            [get_sector_delta(final, s) for s in group_def["expense_sectors"]],
            [group_def["sensitivity"].get(s, 0.5) for s in group_def["expense_sectors"]]
        )

        purchasing_power = income_delta - expense_delta
        housing_impact = get_metric_delta(final, "real_estate_idx")
        employment_impact = get_metric_delta(final, "unemployment_rate")

        results.append(GroupImpact(
            name=group_name,
            purchasing_power=round(purchasing_power, 1),
            income_stability=round(income_delta, 1),
            expense_pressure=round(expense_delta, 1),
            housing_impact=round(housing_impact, 1),
            employment_impact=round(employment_impact, 1),
            severity=classify_severity(purchasing_power, employment_impact),
        ))

    # Citizen satisfaction: weighted by population share
    satisfaction = 50  # baseline
    for r in results:
        weight = SOCIAL_GROUPS[r.name]["population_weight"]
        satisfaction += r.purchasing_power * weight * 0.5
        satisfaction += (100 - abs(r.employment_impact * 10)) * weight * 0.3
    satisfaction = max(0, min(100, round(satisfaction)))

    return results, satisfaction
```

---

## Frontend Changes

### ScenarioPanel → ConversationPanel

Transform the existing `ScenarioPanel.tsx` into a chat-like conversation interface:

- **Message bubbles**: User messages (right-aligned), system messages (left-aligned)
- **Quick-reply buttons**: When system asks follow-up, show clickable options
- **Mode toggle**: "What if?" (Quick) / "Talk Numbers" (Deep) in header
- **Inline param editor**: After parsing, show editable chips for sectors/deltas
- **Confirmation step**: "Run simulation" button after params are set

### New GroupImpactPanel

A new component showing social group impact cards:

- Cards for each group (farmers, students, families, businesses, etc.)
- Each card shows: purchasing power, income stability, expense pressure, housing, employment
- Color-coded severity (green/yellow/red)
- Citizen Satisfaction Score as a prominent gauge
- Expandable: click a card to see the detailed breakdown

### PipelineFlow Update

Add "GROUP_SCORES" stage between "Evidence" and "Recommendation" in the pipeline stepper.

### MapViewport (no changes)

The hex grid map stays as-is. Group impacts are shown alongside, not instead of.

---

## Files to Modify

### Backend (new)
- `backend/engine/nl_engine/__init__.py`
- `backend/engine/nl_engine/router.py`
- `backend/engine/nl_engine/regex_parser.py`
- `backend/engine/nl_engine/spacy_parser.py`
- `backend/engine/nl_engine/ollama_parser.py`
- `backend/engine/nl_engine/domain_maps.py`
- `backend/engine/nl_engine/conversation.py`
- `backend/engine/nl_engine/group_scorer.py`

### Backend (modify)
- `backend/engine/scenario_parser.py` — replace with nl_engine router call
- `backend/app/ws/simulation.py` — add NEEDS_INPUT/INPUT_RESPONSE handling, GROUP_SCORES message
- `backend/engine/runner.py` — add group scoring stage after simulation
- `backend/pyproject.toml` — add spacy dependency

### Frontend (new)
- `frontend/src/components/controls/ConversationPanel.tsx`
- `frontend/src/components/dashboard/GroupImpactPanel.tsx`

### Frontend (modify)
- `frontend/src/components/controls/ScenarioPanel.tsx` — replace with ConversationPanel
- `frontend/src/components/dashboard/PipelineFlow.tsx` — add GROUP_SCORES stage
- `frontend/src/store/simulationStore.ts` — add conversation state, group scores
- `frontend/src/lib/ws.ts` — add NEEDS_INPUT, INPUT_RESPONSE, GROUP_SCORES handlers
- `frontend/src/types/simulation.ts` — add GroupImpact, WSNeedsInput types

---

## Dependencies

### Backend (add)
- `spacy>=3.7` + `en_core_web_sm` model (~12MB)
- `ollama` Python client (optional, for Path 3)

### Frontend (no new dependencies)
- Uses existing React, Zustand, Tremor, deck.gl stack

---

## Implementation Order

1. **domain_maps.py** — Knowledge backbone (no deps, testable standalone)
2. **regex_parser.py** — Upgraded regex (builds on existing parser)
3. **spacy_parser.py** — spaCy integration (new dependency)
4. **router.py** — Intent router (wires 1-3 together)
5. **group_scorer.py** — Post-sim scoring (pure function, testable)
6. **conversation.py** — Conversation state machine
7. **WebSocket integration** — NEEDS_INPUT/INPUT_RESPONSE flow
8. **ollama_parser.py** — Ollama fallback (optional, last)
9. **Frontend ConversationPanel** — Chat UI
10. **Frontend GroupImpactPanel** — Social group cards

---

## Testing Strategy

- **Unit tests**: Each parser path tested independently with sample inputs
- **Integration tests**: Router dispatches correctly, conversation state machine transitions
- **E2E test**: Full flow from NL input → parsed params → simulation → group scores
- **Regression tests**: Ensure existing direct-entry flow still works

---

## Success Criteria

1. "What if petrol prices spike in Mumbai?" → correctly infers transport +15-20%, Mumbai, 24 months
2. "Manufacturing -23%, SEZ policy, Chennai, 36 months" → parses all params directly
3. "Things are bad for farmers" → enters Quick mode, asks 1-2 follow-ups, runs
4. Group impact cards show meaningful differentiation across 7 social groups
5. No Gemini/Ollama API calls for inputs that regex or spaCy can handle
6. Existing simulation flow (direct entry, presets, FDI sliders) still works unchanged

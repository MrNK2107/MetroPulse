# Natural Language Economic Simulation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the regex-only scenario parser with a 3-path NLP pipeline (regex → spaCy → Ollama), add a conversational "what if?" UI with Quick/Deep modes, and compute social group impact scores after simulation.

**Architecture:** Intent router dispatches to cheapest parser that can handle input. Conversation manager handles multi-turn "what if?" dialogue. Post-simulation group scorer derives social group impacts from existing simulation data. WebSocket protocol extended with NEEDS_INPUT and GROUP_SCORES messages.

**Tech Stack:** Python (spaCy, regex, optional Ollama), FastAPI WebSocket, Next.js 14, React, Zustand, TypeScript

---

## File Map

### Backend — New Files
| File | Purpose |
|------|---------|
| `backend/engine/nl_engine/__init__.py` | Package init, exports `route_input` |
| `backend/engine/nl_engine/domain_maps.py` | Synonym maps, cause-effect chains, social group definitions, sentiment words |
| `backend/engine/nl_engine/regex_parser.py` | Path 1: enhanced regex parser with confidence scoring |
| `backend/engine/nl_engine/spacy_parser.py` | Path 2: spaCy NER + domain knowledge extraction |
| `backend/engine/nl_engine/ollama_parser.py` | Path 3: local LLM fallback (optional) |
| `backend/engine/nl_engine/router.py` | Intent router: dispatches to cheapest capable parser |
| `backend/engine/nl_engine/conversation.py` | Conversation state machine, mode detection, follow-up generation |
| `backend/engine/nl_engine/group_scorer.py` | Post-simulation social group impact scoring |
| `backend/tests/unit/test_domain_maps.py` | Tests for domain maps |
| `backend/tests/unit/test_regex_parser.py` | Tests for regex parser |
| `backend/tests/unit/test_spacy_parser.py` | Tests for spaCy parser |
| `backend/tests/unit/test_router.py` | Tests for intent router |
| `backend/tests/unit/test_group_scorer.py` | Tests for group scorer |
| `backend/tests/unit/test_conversation.py` | Tests for conversation manager |

### Backend — Modified Files
| File | Changes |
|------|---------|
| `backend/engine/models.py` | Add `GroupImpact` Pydantic model, add `NEEDS_INPUT`/`INPUT_RESPONSE`/`GROUP_SCORES` message types |
| `backend/engine/scenario_parser.py` | Keep as-is for backward compat; `nl_engine` is the new entry point |
| `backend/app/ws/simulation.py` | Add NEEDS_INPUT/INPUT_RESPONSE handling, GROUP_SCORES stage, use nl_engine router |
| `backend/engine/runner.py` | Add group scoring stage after simulation completes |
| `backend/pyproject.toml` | Add `spacy>=3.7` dependency |

### Frontend — New Files
| File | Purpose |
|------|---------|
| `frontend/src/components/controls/ConversationPanel.tsx` | Chat-like conversation UI replacing ScenarioPanel |
| `frontend/src/components/dashboard/GroupImpactPanel.tsx` | Social group impact cards |

### Frontend — Modified Files
| File | Changes |
|------|---------|
| `frontend/src/types/simulation.ts` | Add `GroupImpact`, `WSNeedsInputMessage`, `WSGroupScoresMessage`, update `WSMessage` union |
| `frontend/src/store/simulationStore.ts` | Add conversation messages state, group scores, conversation mode |
| `frontend/src/lib/ws.ts` | Add `onNeedsInput`, `onGroupScores` callbacks, handle new message types |
| `frontend/src/hooks/useWebSocket.ts` | Wire up new callbacks (onNeedsInput, onGroupScores) |
| `frontend/src/components/dashboard/PipelineFlow.tsx` | Add "Social Impact" stage |
| `frontend/src/app/page.tsx` | Replace ScenarioPanel import with ConversationPanel |

---

## Task 1: Domain Maps

**Files:**
- Create: `backend/engine/nl_engine/__init__.py`
- Create: `backend/engine/nl_engine/domain_maps.py`
- Create: `backend/tests/unit/test_domain_maps.py`

- [ ] **Step 1: Create nl_engine package init**

```python
# backend/engine/nl_engine/__init__.py
"""Natural language engine for MetroPulse scenario parsing."""
```

- [ ] **Step 2: Write failing tests for domain maps**

```python
# backend/tests/unit/test_domain_maps.py
from engine.nl_engine.domain_maps import (
    SECTOR_SYNONYMS,
    CITY_ALIASES,
    CAUSE_EFFECT_CHAINS,
    SOCIAL_GROUPS,
    SENTIMENT_WORDS,
    resolve_sector,
    resolve_city,
    get_event_effects,
)


def test_sector_synonyms_cover_all_sectors():
    """Every canonical sector must appear as a value in SECTOR_SYNONYMS."""
    from engine.models import SECTOR_NAMES
    synonym_targets = set(SECTOR_SYNONYMS.values())
    for sector in SECTOR_NAMES:
        assert sector in synonym_targets, f"Sector {sector} not reachable via synonyms"


def test_resolve_sector_known():
    assert resolve_sector("petrol") == "transport_logistics"
    assert resolve_sector("tech") == "it_ites"
    assert resolve_sector("farm") == "informal"


def test_resolve_sector_unknown():
    assert resolve_sector("quantum computing") is None


def test_city_aliases_include_neighborhoods():
    assert CITY_ALIASES.get("bandra") == "mumbai"
    assert CITY_ALIASES.get("koramangala") == "bengaluru"


def test_resolve_city_alias():
    assert resolve_city("bombay") == "mumbai"
    assert resolve_city("calcutta") == "kolkata"


def test_resolve_city_unknown():
    assert resolve_city("atlantis") is None


def test_cause_effect_chains_positive_and_negative():
    effects = get_event_effects("fuel_price_hike")
    assert effects["transport_logistics"] > 0  # transport costs go up
    assert effects["manufacturing"] < 0         # input costs hurt


def test_get_event_effects_unknown():
    assert get_event_effects("alien_invasion") == {}


def test_social_groups_have_required_keys():
    for name, group in SOCIAL_GROUPS.items():
        assert "income_sectors" in group, f"{name} missing income_sectors"
        assert "expense_sectors" in group, f"{name} missing expense_sectors"
        assert "sensitivity" in group, f"{name} missing sensitivity"
        assert "population_weight" in group, f"{name} missing population_weight"


def test_social_group_weights_sum_to_one():
    total = sum(g["population_weight"] for g in SOCIAL_GROUPS.values())
    assert abs(total - 1.0) < 0.01, f"Population weights sum to {total}, expected ~1.0"


def test_sentiment_words_have_both_directions():
    assert len(SENTIMENT_WORDS["positive"]) > 0
    assert len(SENTIMENT_WORDS["negative"]) > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_domain_maps.py -v`
Expected: FAIL (module not found)

- [ ] **Step 4: Implement domain_maps.py**

```python
# backend/engine/nl_engine/domain_maps.py
"""Shared knowledge backbone for all NLP parsing paths."""
from __future__ import annotations

# ── City aliases (30+ entries including neighborhoods) ──────────────────────

CITY_ALIASES: dict[str, str] = {
    # Primary names
    "bengaluru": "bengaluru", "bangalore": "bengaluru",
    "mumbai": "mumbai", "bombay": "mumbai",
    "delhi": "delhi_ncr", "ncr": "delhi_ncr", "delhi ncr": "delhi_ncr",
    "new delhi": "delhi_ncr",
    "hyderabad": "hyderabad",
    "chennai": "chennai", "madras": "chennai",
    "pune": "pune", "poona": "pune",
    "kolkata": "kolkata", "calcutta": "kolkata",
    "ahmedabad": "ahmedabad", "amdavad": "ahmedabad",
    "jaipur": "jaipur",
    "lucknow": "lucknow",
    "chandigarh": "chandigarh",
    "bhubaneswar": "bhubaneswar",
    # Neighborhoods → city
    "bandra": "mumbai", "andheri": "mumbai", "navi mumbai": "mumbai",
    "thane": "mumbai",
    "koramangala": "bengaluru", "whitefield": "bengaluru",
    "electronic city": "bengaluru", "indiranagar": "bengaluru",
    "gurgaon": "delhi_ncr", "gurugram": "delhi_ncr", "noida": "delhi_ncr",
    "faridabad": "delhi_ncr", "ghaziabad": "delhi_ncr",
    "salt lake": "kolkata", "new town": "kolkata",
    "t nagar": "chennai", "adyar": "chennai",
    "hitech city": "hyderabad", "gachibowli": "hyderabad",
    "hinjewadi": "pune", "kothrud": "pune",
}

# ── Sector synonyms (50+ entries) ──────────────────────────────────────────

SECTOR_SYNONYMS: dict[str, str] = {
    # Transport & fuel
    "petrol": "transport_logistics", "diesel": "transport_logistics",
    "fuel": "transport_logistics", "gas": "transport_logistics",
    "uber": "transport_logistics", "ola": "transport_logistics",
    "auto": "transport_logistics", "truck": "transport_logistics",
    "bus": "transport_logistics", "metro": "transport_logistics",
    "cab": "transport_logistics", "logistics": "transport_logistics",
    "freight": "transport_logistics", "shipping": "transport_logistics",
    "port": "transport_logistics", "rail": "transport_logistics",
    "transport": "transport_logistics", "delivery": "transport_logistics",
    # IT & tech
    "tech": "it_ites", "software": "it_ites", "startup": "it_ites",
    "it": "it_ites", "digital": "it_ites", "ai": "it_ites",
    "coding": "it_ites", "wfh": "it_ites", "outsourcing": "it_ites",
    "ites": "it_ites", "data center": "it_ites", "saas": "it_ites",
    "fintech": "it_ites", "ecommerce": "it_ites",
    # Manufacturing
    "factory": "manufacturing", "industrial": "manufacturing",
    "electricity": "manufacturing", "power": "manufacturing",
    "steel": "manufacturing", "cement": "manufacturing",
    "pharma": "manufacturing", "textile": "manufacturing",
    "automobile": "manufacturing", "assembly": "manufacturing",
    "plant": "manufacturing", "production": "manufacturing",
    # Agriculture & informal
    "crop": "informal", "farm": "informal", "harvest": "informal",
    "monsoon": "informal", "rain": "informal", "drought": "informal",
    "agriculture": "informal", "village": "informal",
    "farmer": "informal", "grain": "informal", "rice": "informal",
    "wheat": "informal", "vegetable": "informal", "livestock": "informal",
    "street vendor": "informal", "casual labor": "informal",
    # Real estate
    "rent": "real_estate", "housing": "real_estate", "flat": "real_estate",
    "construction": "real_estate", "property": "real_estate",
    "apartment": "real_estate", "real estate": "real_estate",
    "builder": "real_estate", "mortgage": "real_estate",
    # Trade & hospitality
    "shop": "trade_hospitality", "restaurant": "trade_hospitality",
    "mall": "trade_hospitality", "tourism": "trade_hospitality",
    "hotel": "trade_hospitality", "market": "trade_hospitality",
    "retail": "trade_hospitality", "cafe": "trade_hospitality",
    "food": "trade_hospitality", "grocery": "trade_hospitality",
    # Public admin
    "government": "public_admin", "govt": "public_admin",
    "subsidy": "public_admin", "tax": "public_admin", "budget": "public_admin",
    "municipal": "public_admin", "civic": "public_admin",
}

# ── Cause-effect chains ────────────────────────────────────────────────────

CAUSE_EFFECT_CHAINS: dict[str, dict[str, float]] = {
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
    "pandemic_lockdown": {
        "trade_hospitality": -0.40,
        "transport_logistics": -0.30,
        "manufacturing": -0.20,
        "real_estate": -0.10,
        "it_ites": +0.10,
    },
    "crop_failure": {
        "informal": -0.30,
        "trade_hospitality": -0.08,
        "transport_logistics": -0.05,
    },
    "flood": {
        "informal": -0.20,
        "real_estate": -0.15,
        "transport_logistics": -0.18,
        "trade_hospitality": -0.10,
    },
    "government_spending": {
        "public_admin": +0.15,
        "construction": +0.10,
        "manufacturing": +0.06,
        "informal": +0.04,
    },
    "global_recession": {
        "it_ites": -0.20,
        "manufacturing": -0.15,
        "trade_hospitality": -0.10,
        "real_estate": -0.08,
    },
}

# ── Event keyword triggers ─────────────────────────────────────────────────

EVENT_KEYWORDS: dict[str, list[str]] = {
    "fuel_price_hike": ["petrol price", "fuel price", "diesel price", "gas price", "oil price"],
    "heavy_rainfall": ["heavy rain", "floods", "flooding", "monsoon flood", "rainfall"],
    "interest_rate_hike": ["interest rate", "repo rate", "loan rate", "emi increase"],
    "subsidy_added": ["subsidy", "government aid", "relief package", "welfare"],
    "unemployment_rise": ["unemployment", "job loss", "layoff", "job cut"],
    "drought": ["drought", "water scarcity", "no rain", "crop failure"],
    "tech_boom": ["tech boom", "startup boom", "it boom", "digital boom"],
    "pandemic_lockdown": ["pandemic", "lockdown", "covid", "curfew"],
    "crop_failure": ["crop failure", "harvest fail", "crop loss"],
    "flood": ["flood", "inundation", "waterlogging"],
    "government_spending": ["government spending", "infra push", "public investment"],
    "global_recession": ["recession", "global downturn", "economic crisis"],
}

# ── Sentiment words (magnitude inference) ──────────────────────────────────

SENTIMENT_WORDS: dict[str, dict[str, list[str]]] = {
    "positive": {
        "extreme": ["skyrocketed", "surged", "exploded", "boom", "revolution"],
        "strong": ["significant growth", "major boost", "sharp rise", "soared"],
        "moderate": ["increase", "rise", "growth", "improve", "boost", "positive"],
        "mild": ["slight increase", "minor improvement", "gradual growth", "uptick"],
    },
    "negative": {
        "extreme": ["crashed", "devastating", "collapse", "catastrophe", "meltdown"],
        "strong": ["sharp decline", "major drop", "plummeted", "crisis"],
        "moderate": ["decline", "drop", "falls", "fall", "reduced", "decrease"],
        "mild": ["slight drop", "minor decline", "dip", "slowdown"],
    },
}

MAGNITUDE_MAP: dict[str, float] = {
    "extreme": 40.0,
    "strong": 25.0,
    "moderate": 15.0,
    "mild": 8.0,
}

# ── Social group definitions ───────────────────────────────────────────────

SOCIAL_GROUPS: dict[str, dict] = {
    "farmers": {
        "income_sectors": ["informal"],
        "expense_sectors": ["transport_logistics", "manufacturing"],
        "sensitivity": {"rainfall": 0.8, "fuel": 0.6, "subsidy": 0.7, "drought": 0.9},
        "population_weight": 0.42,
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
        "expense_sectors": ["manufacturing"],
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

# ── Follow-up question templates ───────────────────────────────────────────

FOLLOW_UP_TEMPLATES: dict[str, str] = {
    "missing_city": "Which city are you thinking about?",
    "missing_severity": "How big should this be — mild, moderate, or severe?",
    "missing_sector": "Which part of the economy should I focus on?",
    "ambiguous_event": "I detected {event}. Which sectors get hit hardest?",
    "missing_horizon": "How far out — 6 months, a year, or 2 years?",
}


# ── Helper functions ───────────────────────────────────────────────────────

def resolve_sector(word: str) -> str | None:
    """Map a word to a canonical sector name, or None."""
    return SECTOR_SYNONYMS.get(word.lower())


def resolve_city(text: str) -> str | None:
    """Map a city name or alias to canonical city ID, or None."""
    return CITY_ALIASES.get(text.lower().strip())


def get_event_effects(event_name: str) -> dict[str, float]:
    """Return sector deltas for a known event, or empty dict."""
    return dict(CAUSE_EFFECT_CHAINS.get(event_name, {}))


def detect_event(text: str) -> str | None:
    """Detect an event from natural language text. Returns event name or None."""
    lowered = text.lower()
    for event_name, keywords in EVENT_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return event_name
    return None


def detect_sentiment(text: str) -> tuple[str, float]:
    """Detect sentiment direction and magnitude from text.
    Returns (direction, magnitude) where direction is 'positive'/'negative'/'neutral'.
    """
    lowered = text.lower()
    for direction in ("negative", "positive"):
        for level, words in SENTIMENT_WORDS[direction].items():
            if any(w in lowered for w in words):
                return direction, MAGNITUDE_MAP[level]
    return "neutral", 0.0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_domain_maps.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/engine/nl_engine/__init__.py backend/engine/nl_engine/domain_maps.py backend/tests/unit/test_domain_maps.py
git commit -m "feat(engine): add domain maps knowledge backbone for NL parsing"
```

---

## Task 2: Enhanced Regex Parser

**Files:**
- Create: `backend/engine/nl_engine/regex_parser.py`
- Create: `backend/tests/unit/test_regex_parser.py`

- [ ] **Step 1: Write failing tests for regex parser**

```python
# backend/tests/unit/test_regex_parser.py
import pytest
from engine.nl_engine.regex_parser import RegexParser


@pytest.fixture
def parser():
    return RegexParser()


def test_parse_explicit_percentage(parser):
    result = parser.parse("Manufacturing drops 40% in Mumbai")
    assert result.city == "mumbai"
    assert result.sector_deltas["manufacturing"] == -40.0
    assert result.confidence >= 0.8


def test_parse_positive_delta(parser):
    result = parser.parse("IT sector grows 25% in Bengaluru")
    assert result.city == "bengaluru"
    assert result.sector_deltas["it_ites"] == 25.0


def test_parse_synonym_petrol(parser):
    result = parser.parse("Petrol prices spike in Chennai")
    assert result.city == "chennai"
    assert result.sector_deltas["transport_logistics"] != 0.0


def test_parse_cause_effect(parser):
    result = parser.parse("Heavy rainfall devastates Mumbai")
    assert result.city == "mumbai"
    assert result.sector_deltas["informal"] < 0


def test_parse_no_city_returns_low_confidence(parser):
    result = parser.parse("Manufacturing drops 40%")
    assert result.confidence < 0.5


def test_parse_neighborhood_alias(parser):
    result = parser.parse("Tech boom in Koramangala")
    assert result.city == "bengaluru"


def test_parse_horizon_explicit(parser):
    result = parser.parse("IT grows 20% in Hyderabad for 36 months")
    assert result.city == "hyderabad"
    assert result.horizon_months == 36


def test_parse_horizon_default(parser):
    result = parser.parse("Manufacturing drops in Mumbai")
    assert result.horizon_months == 24


def test_parse_policy_detection(parser):
    result = parser.parse("SEZ policy applied in Chennai with manufacturing +15%")
    assert "SEZ Notification" in result.policies_active


def test_parse_vague_growth(parser):
    result = parser.parse("Tech boom in Bangalore")
    assert result.city == "bengaluru"
    assert result.sector_deltas["it_ites"] > 0


def test_parse_increased_by_format(parser):
    result = parser.parse("Fuel increased by 15% in Delhi")
    assert result.city == "delhi_ncr"
    assert result.sector_deltas["transport_logistics"] == 15.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_regex_parser.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement regex_parser.py**

```python
# backend/engine/nl_engine/regex_parser.py
"""Path 1: Enhanced regex parser with domain knowledge integration."""
from __future__ import annotations

import re

from engine.models import ParsedScenario, SECTOR_NAMES
from engine.nl_engine.domain_maps import (
    CITY_ALIASES,
    SECTOR_SYNONYMS,
    CAUSE_EFFECT_CHAINS,
    EVENT_KEYWORDS,
    SENTIMENT_WORDS,
    MAGNITUDE_MAP,
    detect_event,
    detect_sentiment,
)

# Policy keywords (from existing scenario_parser.py)
POLICY_KEYWORDS: dict[str, list[str]] = {
    "SEZ Notification": ["sez", "special economic zone"],
    "Smart City Mission": ["smart city"],
    "AMRUT": ["amrut", "water", "sanitation"],
    "RERA Compliance": ["rera"],
    "PM Awas Yojana": ["pmay", "awas", "affordable housing", "housing scheme"],
    "Make in India": ["make in india"],
    "Digital India": ["digital india"],
}

NEGATIVE_WORDS = [
    "drop", "drops", "decline", "falls", "fall", "cut", "loss", "crisis",
    "shock", "reduce", "reduced", "devastate", "crash", "plummet", "slump",
]
POSITIVE_WORDS = [
    "increase", "increases", "rise", "rises", "boom", "growth", "boost",
    "push", "investment", "improve", "surge", "soar", "gain",
]


class RegexParser:
    """Enhanced regex-based scenario parser with confidence scoring."""

    def parse(self, text: str) -> ParsedScenario:
        lowered = text.lower()

        # Extract city
        city = self._extract_city(lowered)

        # Extract sector deltas via synonyms + explicit percentages
        sector_deltas = {s: 0.0 for s in SECTOR_NAMES}
        mentioned_sectors: list[str] = []
        for word in lowered.split():
            sector = SECTOR_SYNONYMS.get(word)
            if sector and sector not in mentioned_sectors:
                mentioned_sectors.append(sector)

        # Also check multi-word synonyms
        for synonym, sector in SECTOR_SYNONYMS.items():
            if " " in synonym and synonym in lowered and sector not in mentioned_sectors:
                mentioned_sectors.append(sector)

        # Extract explicit percentages
        percent_match = re.search(r"([+-]?\d{1,3})\s*%", lowered)
        explicit_delta = float(percent_match.group(1)) if percent_match else None

        # For each mentioned sector, infer delta
        for sector in mentioned_sectors:
            sector_deltas[sector] = self._infer_delta(lowered, explicit_delta)

        # Cause-effect chain detection
        event = detect_event(lowered)
        if event:
            effects = CAUSE_EFFECT_CHAINS.get(event, {})
            for sector, delta in effects.items():
                if sector not in mentioned_sectors:
                    mentioned_sectors.append(sector)
                    sector_deltas[sector] = delta * 100  # Convert to percentage

        # Sentiment-based delta if no explicit number and sectors found
        if explicit_delta is None and mentioned_sectors:
            direction, magnitude = detect_sentiment(lowered)
            if direction != "neutral":
                for sector in mentioned_sectors:
                    if sector_deltas[sector] == 0.0:
                        sector_deltas[sector] = magnitude if direction == "positive" else -magnitude

        # Vague prompt handling
        if not mentioned_sectors:
            if any(w in lowered for w in ["boom", "growth", "investment", "improve"]):
                sector_deltas["it_ites"] = 25.0
                sector_deltas["manufacturing"] = 10.0
                mentioned_sectors = ["it_ites", "manufacturing"]
            elif any(w in lowered for w in ["crisis", "shock", "recession", "decline"]):
                sector_deltas["it_ites"] = -15.0
                sector_deltas["trade_hospitality"] = -10.0
                mentioned_sectors = ["it_ites", "trade_hospitality"]

        # Policy detection
        policies = [
            policy
            for policy, keywords in POLICY_KEYWORDS.items()
            if any(kw in lowered for kw in keywords)
        ]

        # Horizon extraction
        horizon = self._extract_horizon(lowered)

        # Confidence scoring
        confidence = self._compute_confidence(city, mentioned_sectors, explicit_delta)

        keywords = [city, *mentioned_sectors, *policies] if city else [*mentioned_sectors, *policies]

        return ParsedScenario(
            city=city or "",
            sector_deltas=sector_deltas,
            policies_active=policies,
            public_works_zone=None,
            horizon_months=horizon,
            causal_chain=text.strip(),
            keywords=[k for k in keywords if k],
            confidence=confidence,
            assumptions=[],
        )

    def _extract_city(self, text: str) -> str | None:
        # Try multi-word aliases first (longer matches)
        sorted_aliases = sorted(CITY_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
        for alias, city_id in sorted_aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text):
                return city_id
        return None

    def _infer_delta(self, text: str, explicit_delta: float | None) -> float:
        if explicit_delta is not None:
            magnitude = abs(explicit_delta)
        else:
            magnitude = 15.0  # default when no number found

        if magnitude > 50:
            magnitude = 50.0

        if any(w in text for w in NEGATIVE_WORDS):
            return -magnitude
        if any(w in text for w in POSITIVE_WORDS):
            return magnitude
        return magnitude

    def _extract_horizon(self, text: str) -> int:
        match = re.search(r"(\d{1,2})\s*(month|months|m)\b", text)
        if match:
            value = int(match.group(1))
            return min([6, 12, 24, 60], key=lambda x: abs(x - value))
        match = re.search(r"(\d)\s*(year|years|yr|yrs)\b", text)
        if match:
            value = int(match.group(1)) * 12
            return min([6, 12, 24, 60], key=lambda x: abs(x - value))
        return 24

    def _compute_confidence(
        self, city: str | None, sectors: list[str], explicit_delta: float | None
    ) -> str:
        score = 0.0
        if city:
            score += 0.4
        if sectors:
            score += 0.3
        if explicit_delta is not None:
            score += 0.2
        if score >= 0.7:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_regex_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nl_engine/regex_parser.py backend/tests/unit/test_regex_parser.py
git commit -m "feat(engine): add enhanced regex parser with domain knowledge"
```

---

## Task 3: spaCy Parser

**Files:**
- Create: `backend/engine/nl_engine/spacy_parser.py`
- Create: `backend/tests/unit/test_spacy_parser.py`
- Modify: `backend/pyproject.toml` (add spacy dependency)

- [ ] **Step 1: Add spacy dependency**

Add to `backend/pyproject.toml` dependencies list:
```
"spacy>=3.7,<4.0",
```

- [ ] **Step 2: Install spacy and download model**

Run: `cd backend && pip install spacy && python -m spacy download en_core_web_sm`

- [ ] **Step 3: Write failing tests for spaCy parser**

```python
# backend/tests/unit/test_spacy_parser.py
import pytest
from engine.nl_engine.spacy_parser import SpacyParser


@pytest.fixture
def parser():
    return SpacyParser()


def test_extract_city_gpe(parser):
    result = parser.parse("What if there is a tech boom in Mumbai?")
    assert result.city == "mumbai"


def test_extract_sector_from_noun_phrase(parser):
    result = parser.parse("Petrol prices are skyrocketing in Delhi")
    assert result.sector_deltas["transport_logistics"] != 0.0


def test_extract_percentage(parser):
    result = parser.parse("Manufacturing increased by 20% in Chennai")
    assert result.sector_deltas["manufacturing"] == 20.0


def test_magnitude_inference_strong_negative(parser):
    result = parser.parse("The devastating flood destroyed Mumbai's economy")
    assert result.city == "mumbai"
    # Should infer negative deltas
    total_delta = sum(result.sector_deltas.values())
    assert total_delta < 0


def test_confidence_with_city_and_sectors(parser):
    result = parser.parse("IT sector grows in Bengaluru")
    assert result.confidence >= 0.6


def test_confidence_low_without_city(parser):
    result = parser.parse("Things are getting worse")
    assert result.confidence < 0.5


def test_fuzzy_city_match(parser):
    result = parser.parse("What if it floods in Bombai?")  # typo
    assert result.city == "mumbai"
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_spacy_parser.py -v`
Expected: FAIL (module not found)

- [ ] **Step 5: Implement spacy_parser.py**

```python
# backend/engine/nl_engine/spacy_parser.py
"""Path 2: spaCy NER + domain knowledge extraction."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from engine.models import ParsedScenario, SECTOR_NAMES
from engine.nl_engine.domain_maps import (
    CITY_ALIASES,
    SECTOR_SYNONYMS,
    CAUSE_EFFECT_CHAINS,
    SENTIMENT_WORDS,
    MAGNITUDE_MAP,
    detect_event,
    detect_sentiment,
)

# Policy keywords
POLICY_KEYWORDS: dict[str, list[str]] = {
    "SEZ Notification": ["sez", "special economic zone"],
    "Smart City Mission": ["smart city"],
    "AMRUT": ["amrut"],
    "RERA Compliance": ["rera"],
    "PM Awas Yojana": ["pmay", "awas", "affordable housing"],
    "Make in India": ["make in india"],
    "Digital India": ["digital india"],
}

# Magnitude adjectives
MAGNITUDE_ADJECTIVES: dict[str, float] = {
    "skyrocketed": 40, "surged": 35, "exploded": 40, "crashed": -40,
    "devastating": -35, "plummeted": -35, "collapse": -40,
    "significant": 25, "major": 25, "sharp": 25, "soared": 30,
    "slight": 8, "minor": 8, "gradual": 8, "mild": 8,
    "moderate": 15, "steady": 12,
}


def _fuzzy_match_city(text: str, threshold: float = 0.75) -> str | None:
    """Fuzzy match a city name with Levenshtein-like ratio."""
    best_match = None
    best_score = 0.0
    for alias, city_id in CITY_ALIASES.items():
        score = SequenceMatcher(None, text.lower(), alias).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = city_id
    return best_match


class SpacyParser:
    """spaCy-based NLP parser for natural language scenario input."""

    def __init__(self) -> None:
        self._nlp = None

    @property
    def nlp(self) -> Any:
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except (ImportError, OSError):
                raise RuntimeError(
                    "spaCy or en_core_web_sm not installed. "
                    "Run: pip install spacy && python -m spacy download en_core_web_sm"
                )
        return self._nlp

    def parse(self, text: str) -> ParsedScenario:
        doc = self.nlp(text)

        # City detection via GPE entities
        city = self._extract_city(doc, text)

        # Sector detection via noun phrases + synonyms
        sectors_found = self._extract_sectors(doc, text)

        # Delta extraction via NUM entities + context
        explicit_delta = self._extract_delta(doc)

        # Event detection
        event = detect_event(text)

        # Build sector deltas
        sector_deltas = {s: 0.0 for s in SECTOR_NAMES}
        mentioned_sectors: list[str] = []

        for sector in sectors_found:
            mentioned_sectors.append(sector)
            if explicit_delta is not None:
                sector_deltas[sector] = self._apply_direction(text, explicit_delta)
            else:
                # Use magnitude adjective or sentiment
                magnitude = self._infer_magnitude(text)
                sector_deltas[sector] = magnitude

        # Apply cause-effect chains
        if event:
            effects = CAUSE_EFFECT_CHAINS.get(event, {})
            for sector, delta in effects.items():
                if sector not in mentioned_sectors:
                    mentioned_sectors.append(sector)
                    sector_deltas[sector] = delta * 100

        # Vague prompt fallback
        if not mentioned_sectors and not event:
            direction, magnitude = detect_sentiment(text)
            if direction != "neutral":
                sector_deltas["it_ites"] = magnitude if direction == "positive" else -magnitude
                sector_deltas["manufacturing"] = (magnitude * 0.6) if direction == "positive" else -(magnitude * 0.6)
                mentioned_sectors = ["it_ites", "manufacturing"]

        # Policy detection
        policies = [
            policy
            for policy, keywords in POLICY_KEYWORDS.items()
            if any(kw in text.lower() for kw in keywords)
        ]

        # Confidence scoring
        confidence_score = self._compute_confidence(city, mentioned_sectors, explicit_delta)

        keywords = []
        if city:
            keywords.append(city)
        keywords.extend(mentioned_sectors)
        keywords.extend(policies)

        return ParsedScenario(
            city=city or "",
            sector_deltas=sector_deltas,
            policies_active=policies,
            public_works_zone=None,
            horizon_months=24,
            causal_chain=text.strip(),
            keywords=[k for k in keywords if k],
            confidence=confidence_score,
            assumptions=[],
        )

    def _extract_city(self, doc: Any, text: str) -> str | None:
        # Try GPE entities first
        for ent in doc.ents:
            if ent.label_ == "GPE":
                city_id = CITY_ALIASES.get(ent.text.lower())
                if city_id:
                    return city_id
                # Fuzzy match
                city_id = _fuzzy_match_city(ent.text)
                if city_id:
                    return city_id

        # Fallback: fuzzy match all tokens
        for token in doc:
            if token.is_alpha and len(token.text) > 3:
                city_id = CITY_ALIASES.get(token.text.lower())
                if city_id:
                    return city_id

        return None

    def _extract_sectors(self, doc: Any, text: str) -> list[str]:
        sectors = set()
        lowered = text.lower()

        # Check noun phrases
        for chunk in doc.noun_chunks:
            chunk_lower = chunk.text.lower()
            for synonym, sector in SECTOR_SYNONYMS.items():
                if synonym in chunk_lower:
                    sectors.add(sector)

        # Check individual tokens
        for token in doc:
            if token.is_alpha:
                sector = SECTOR_SYNONYMS.get(token.text.lower())
                if sector:
                    sectors.add(sector)

        return list(sectors)

    def _extract_delta(self, doc: Any) -> float | None:
        for ent in doc.ents:
            if ent.label_ == "PERCENT":
                num_text = ent.text.replace("%", "").strip()
                try:
                    return float(num_text)
                except ValueError:
                    pass

        # Also check raw NUM entities
        for ent in doc.ents:
            if ent.label_ == "NUM":
                num_text = ent.text.replace("%", "").strip()
                try:
                    val = float(num_text)
                    if 1 <= val <= 100:
                        return val
                except ValueError:
                    pass

        return None

    def _apply_direction(self, text: str, magnitude: float) -> float:
        lowered = text.lower()
        negative = ["drop", "decline", "falls", "fall", "cut", "crisis", "shock",
                     "reduce", "crash", "plummet", "devastate", "slump"]
        positive = ["increase", "rise", "growth", "boom", "boost", "surge",
                     "soar", "improve", "gain", "investment"]
        if any(w in lowered for w in negative):
            return -abs(magnitude)
        if any(w in lowered for w in positive):
            return abs(magnitude)
        return magnitude

    def _infer_magnitude(self, text: str) -> float:
        lowered = text.lower()
        for word, magnitude in MAGNITUDE_ADJECTIVES.items():
            if word in lowered:
                return magnitude
        # Fall back to sentiment detection
        direction, magnitude = detect_sentiment(text)
        if direction == "positive":
            return magnitude
        if direction == "negative":
            return -magnitude
        return 15.0  # default moderate

    def _compute_confidence(
        self, city: str | None, sectors: list[str], delta: float | None
    ) -> str:
        score = 0.0
        if city:
            score += 0.3
        if sectors:
            score += 0.4 * min(len(sectors) / 3, 1.0)
        if delta is not None:
            score += 0.2
        if score >= 0.7:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_spacy_parser.py -v`
Expected: All PASS (skipped if spaCy not installed)

- [ ] **Step 7: Commit**

```bash
git add backend/engine/nl_engine/spacy_parser.py backend/tests/unit/test_spacy_parser.py backend/pyproject.toml
git commit -m "feat(engine): add spaCy NLP parser with NER extraction"
```

---

## Task 4: Intent Router

**Files:**
- Create: `backend/engine/nl_engine/router.py`
- Create: `backend/tests/unit/test_router.py`

- [ ] **Step 1: Write failing tests for router**

```python
# backend/tests/unit/test_router.py
import pytest
from engine.nl_engine.router import IntentRouter


@pytest.fixture
def router():
    return IntentRouter()


@pytest.mark.asyncio
async def test_regex_path_for_explicit_input(router):
    result, confidence = await router.route("Manufacturing drops 40% in Mumbai")
    assert result.city == "mumbai"
    assert confidence >= 0.8


@pytest.mark.asyncio
async def test_spacy_path_for_natural_language(router):
    result, confidence = await router.route("What if petrol prices spike in Delhi?")
    assert result.city == "delhi_ncr"
    assert result.sector_deltas["transport_logistics"] != 0.0


@pytest.mark.asyncio
async def test_router_returns_parsed_scenario(router):
    result, confidence = await router.route("Tech boom in Bengaluru")
    assert result.city == "bengaluru"
    assert confidence > 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_router.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement router.py**

```python
# backend/engine/nl_engine/router.py
"""Intent router: dispatches to cheapest parser that can handle input."""
from __future__ import annotations

import logging

from engine.models import ParsedScenario
from engine.nl_engine.regex_parser import RegexParser

logger = logging.getLogger(__name__)

# Confidence thresholds
REGEX_CONFIDENCE_THRESHOLD = 0.8
SPACY_CONFIDENCE_THRESHOLD = 0.6


class IntentRouter:
    """Three-path intent router: regex → spaCy → Ollama fallback."""

    def __init__(self) -> None:
        self._regex = RegexParser()
        self._spacy = None  # lazy load
        self._ollama = None  # lazy load

    @property
    def spacy(self):
        if self._spacy is None:
            from engine.nl_engine.spacy_parser import SpacyParser
            self._spacy = SpacyParser()
        return self._spacy

    async def route(self, text: str) -> tuple[ParsedScenario, float]:
        """Route input to cheapest capable parser. Returns (scenario, confidence)."""

        # Path 1: Regex (instant, no deps)
        regex_result = self._regex.parse(text)
        regex_confidence = self._confidence_score(regex_result)
        if regex_confidence >= REGEX_CONFIDENCE_THRESHOLD:
            logger.debug("Router: regex path (confidence=%.2f)", regex_confidence)
            return regex_result, regex_confidence

        # Path 2: spaCy (fast local NLP)
        try:
            spacy_result = self.spacy.parse(text)
            spacy_confidence = self._confidence_score(spacy_result)
            if spacy_confidence >= SPACY_CONFIDENCE_THRESHOLD:
                logger.debug("Router: spaCy path (confidence=%.2f)", spacy_confidence)
                return spacy_result, spacy_confidence
        except RuntimeError:
            logger.warning("spaCy not available, skipping Path 2")

        # Path 3: Return best of regex/spaCy with warning
        # Ollama fallback is handled at the WebSocket layer
        if regex_confidence >= spacy_confidence:
            logger.debug("Router: returning regex result (low confidence=%.2f)", regex_confidence)
            return regex_result, regex_confidence
        logger.debug("Router: returning spaCy result (low confidence=%.2f)", spacy_confidence)
        return spacy_result, spacy_confidence

    def _confidence_score(self, parsed: ParsedScenario) -> float:
        """Compute numeric confidence from parsed scenario."""
        score = 0.0
        if parsed.city:
            score += 0.3
        active_sectors = [s for s, d in parsed.sector_deltas.items() if d != 0.0]
        if active_sectors:
            score += 0.4 * min(len(active_sectors) / 3, 1.0)
        if parsed.policies_active:
            score += 0.1
        if parsed.confidence == "high":
            score += 0.2
        elif parsed.confidence == "medium":
            score += 0.1
        return min(score, 1.0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_router.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nl_engine/router.py backend/tests/unit/test_router.py
git commit -m "feat(engine): add intent router with 3-path dispatch"
```

---

## Task 5: Group Scorer

**Files:**
- Create: `backend/engine/nl_engine/group_scorer.py`
- Create: `backend/tests/unit/test_group_scorer.py`

- [ ] **Step 1: Write failing tests for group scorer**

```python
# backend/tests/unit/test_group_scorer.py
import pytest
from engine.nl_engine.group_scorer import GroupImpact, score_groups, classify_severity
from engine.models import AggregateMetrics


def make_metrics(**overrides) -> AggregateMetrics:
    defaults = {
        "gdpDelta": 0.0,
        "unemploymentRate": 0.0,
        "realEstateIndex": 1.0,
        "transitCongestion": 0.5,
        "informalEmployment": 0.3,
        "housingAffordability": 1.0,
        "floodDisruption": 0.0,
        "migrationBalance": 0.0,
    }
    defaults.update(overrides)
    return AggregateMetrics(**defaults)


def make_sector_deltas(**overrides) -> dict[str, float]:
    defaults = {
        "it_ites": 0.0,
        "manufacturing": 0.0,
        "real_estate": 0.0,
        "trade_hospitality": 0.0,
        "transport_logistics": 0.0,
        "informal": 0.0,
        "public_admin": 0.0,
    }
    defaults.update(overrides)
    return defaults


def test_score_groups_returns_all_groups():
    metrics = make_metrics()
    deltas = make_sector_deltas()
    groups = score_groups(deltas, metrics)
    group_names = [g.name for g in groups]
    assert "farmers" in group_names
    assert "students" in group_names
    assert "small_businesses" in group_names
    assert len(groups) == 7


def test_farmers_hurt_by_fuel_hike():
    metrics = make_metrics(unemploymentRate=5.0)
    deltas = make_sector_deltas(transport_logistics=20.0, informal=-10.0)
    groups = score_groups(deltas, metrics)
    farmers = next(g for g in groups if g.name == "farmers")
    # Income down (informal -10), expenses up (transport +20) → purchasing power negative
    assert farmers.purchasing_power < 0


def test_it_sector_benefits_from_boom():
    metrics = make_metrics(unemploymentRate=-2.0)
    deltas = make_sector_deltas(it_ites=30.0, real_estate=15.0)
    groups = score_groups(deltas, metrics)
    students = next(g for g in groups if g.name == "students")
    # Income up (IT +30), expenses somewhat up (real estate +15) → net positive
    assert students.purchasing_power > 0


def test_classify_severity():
    assert classify_severity(-20.0, 10.0) == "high"
    assert classify_severity(-8.0, 3.0) == "moderate"
    assert classify_severity(-2.0, 1.0) == "low"
    assert classify_severity(5.0, -1.0) == "low"


def test_citizen_satisfaction_bounded():
    metrics = make_metrics()
    deltas = make_sector_deltas(informal=-50.0, transport_logistics=-50.0)
    groups = score_groups(deltas, metrics)
    satisfaction = sum(
        g.purchasing_power * 0.5 + (100 - abs(g.employment_impact * 10)) * 0.3
        for g in groups
    )
    # The actual function should bound this to 0-100
    from engine.nl_engine.group_scorer import compute_satisfaction
    score = compute_satisfaction(groups)
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_group_scorer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement group_scorer.py**

```python
# backend/engine/nl_engine/group_scorer.py
"""Post-simulation social group impact scoring."""
from __future__ import annotations

from dataclasses import dataclass

from engine.models import AggregateMetrics, SECTOR_NAMES
from engine.nl_engine.domain_maps import SOCIAL_GROUPS


@dataclass
class GroupImpact:
    """Impact metrics for a single social group."""
    name: str
    purchasing_power: float
    income_stability: float
    expense_pressure: float
    housing_impact: float
    employment_impact: float
    severity: str  # "low" | "moderate" | "high"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "purchasing_power": self.purchasing_power,
            "income_stability": self.income_stability,
            "expense_pressure": self.expense_pressure,
            "housing_impact": self.housing_impact,
            "employment_impact": self.employment_impact,
            "severity": self.severity,
        }


def classify_severity(purchasing_power: float, employment_impact: float) -> str:
    """Classify impact severity based on purchasing power and employment."""
    combined = abs(purchasing_power) + abs(employment_impact)
    if combined >= 15:
        return "high"
    if combined >= 7:
        return "moderate"
    return "low"


def weighted_avg(values: list[float], weights: list[float]) -> float:
    """Compute weighted average. Returns 0 if inputs are empty."""
    if not values:
        return 0.0
    total_weight = sum(weights)
    if total_weight == 0:
        return sum(values) / len(values)
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def score_groups(
    sector_deltas: dict[str, float],
    metrics: AggregateMetrics,
) -> list[GroupImpact]:
    """Compute per-group impacts from simulation results.

    Args:
        sector_deltas: Final sector delta percentages from simulation.
        metrics: Aggregate metrics from the final simulation frame.

    Returns:
        List of GroupImpact for each social group.
    """
    results = []

    for group_name, group_def in SOCIAL_GROUPS.items():
        # Income: weighted average of income sector deltas
        income_values = [sector_deltas.get(s, 0.0) for s in group_def["income_sectors"]]
        income_weights = [group_def["sensitivity"].get(s, 0.5) for s in group_def["income_sectors"]]
        income_delta = weighted_avg(income_values, income_weights)

        # Expenses: weighted average of expense sector deltas (inverted)
        expense_values = [sector_deltas.get(s, 0.0) for s in group_def["expense_sectors"]]
        expense_weights = [group_def["sensitivity"].get(s, 0.5) for s in group_def["expense_sectors"]]
        expense_delta = weighted_avg(expense_values, expense_weights)

        purchasing_power = income_delta - expense_delta
        housing_impact = (metrics.realEstateIndex - 1.0) * 100  # baseline is 1.0
        employment_impact = metrics.unemploymentRate

        results.append(GroupImpact(
            name=group_name,
            purchasing_power=round(purchasing_power, 1),
            income_stability=round(income_delta, 1),
            expense_pressure=round(expense_delta, 1),
            housing_impact=round(housing_impact, 1),
            employment_impact=round(employment_impact, 1),
            severity=classify_severity(purchasing_power, employment_impact),
        ))

    return results


def compute_satisfaction(groups: list[GroupImpact]) -> int:
    """Compute citizen satisfaction score (0-100) from group impacts."""
    satisfaction = 50.0  # baseline
    for g in groups:
        group_def = SOCIAL_GROUPS.get(g.name, {})
        weight = group_def.get("population_weight", 0.05)
        satisfaction += g.purchasing_power * weight * 0.5
        satisfaction += (100 - abs(g.employment_impact * 10)) * weight * 0.3
    return max(0, min(100, round(satisfaction)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_group_scorer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nl_engine/group_scorer.py backend/tests/unit/test_group_scorer.py
git commit -m "feat(engine): add social group impact scorer"
```

---

## Task 6: Conversation Manager

**Files:**
- Create: `backend/engine/nl_engine/conversation.py`
- Create: `backend/tests/unit/test_conversation.py`

- [ ] **Step 1: Write failing tests for conversation manager**

```python
# backend/tests/unit/test_conversation.py
import pytest
from engine.nl_engine.conversation import ConversationManager, ConversationMode


def test_detect_deep_mode_with_numbers():
    mgr = ConversationManager()
    mode = mgr.detect_mode("Manufacturing -23%, SEZ policy, Chennai, 36 months")
    assert mode == ConversationMode.DEEP


def test_detect_quick_mode_with_vague_language():
    mgr = ConversationManager()
    mode = mgr.detect_mode("What if it floods in Mumbai?")
    assert mode == ConversationMode.QUICK


def test_detect_quick_mode_default():
    mgr = ConversationManager()
    mode = mgr.detect_mode("Things are bad")
    assert mode == ConversationMode.QUICK


def test_needs_followup_when_no_city():
    mgr = ConversationManager()
    from engine.models import ParsedScenario
    parsed = ParsedScenario(
        city="",
        sector_deltas={"it_ites": 25.0},
        confidence="low",
    )
    question = mgr.get_followup(parsed)
    assert question is not None
    assert "city" in question.lower() or "which" in question.lower()


def test_no_followup_when_complete():
    mgr = ConversationManager()
    from engine.models import ParsedScenario
    parsed = ParsedScenario(
        city="mumbai",
        sector_deltas={"it_ites": 25.0, "manufacturing": 0.0, "real_estate": 0.0,
                       "trade_hospitality": 0.0, "transport_logistics": 0.0,
                       "informal": 0.0, "public_admin": 0.0},
        horizon_months=24,
        confidence="high",
    )
    question = mgr.get_followup(parsed)
    assert question is None


def test_followup_options_for_severity():
    mgr = ConversationManager()
    from engine.models import ParsedScenario
    parsed = ParsedScenario(
        city="mumbai",
        sector_deltas={"it_ites": 0.0, "manufacturing": 0.0, "real_estate": 0.0,
                       "trade_hospitality": 0.0, "transport_logistics": 0.0,
                       "informal": 0.0, "public_admin": 0.0},
        horizon_months=24,
        confidence="medium",
    )
    question = mgr.get_followup(parsed)
    # Should ask about severity or sectors
    assert question is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_conversation.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement conversation.py**

```python
# backend/engine/nl_engine/conversation.py
"""Conversation state machine for 'what if?' dialogue."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

from engine.models import ParsedScenario
from engine.nl_engine.domain_maps import FOLLOW_UP_TEMPLATES


class ConversationMode(str, Enum):
    QUICK = "quick"
    DEEP = "deep"


class ConversationState(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    NEEDS_INPUT = "needs_input"
    CONFIRMED = "confirmed"
    SIMULATING = "simulating"
    DONE = "done"


class ConversationManager:
    """Manages conversation flow and mode detection."""

    def __init__(self) -> None:
        self.state = ConversationState.IDLE
        self.mode = ConversationMode.QUICK
        self.turn_count = 0

    def detect_mode(self, text: str) -> ConversationMode:
        """Detect whether input is Quick or Deep mode."""
        # Deep mode indicators
        has_numbers = bool(re.search(r"\d+%?", text))
        has_mode_keywords = any(
            w in text.lower() for w in ["deep mode", "talk numbers", "precise"]
        )

        if has_numbers or has_mode_keywords:
            return ConversationMode.DEEP

        # Quick mode indicators
        has_vague_language = any(
            w in text.lower()
            for w in ["what if", "imagine", "suppose", "happens", "affect", "impact"]
        )
        if has_vague_language:
            return ConversationMode.QUICK

        return ConversationMode.QUICK  # default

    def get_followup(self, parsed: ParsedScenario) -> str | None:
        """Generate a follow-up question if params are incomplete. Returns None if complete."""
        # Check for missing city
        if not parsed.city:
            return FOLLOW_UP_TEMPLATES["missing_city"]

        # Check for no sectors at all
        active_sectors = [s for s, d in parsed.sector_deltas.items() if d != 0.0]
        if not active_sectors:
            return FOLLOW_UP_TEMPLATES["missing_sector"]

        # If confidence is medium and no explicit delta, ask about severity
        if parsed.confidence == "medium":
            has_explicit_delta = any(
                abs(d) > 0 and abs(d) != 15.0  # 15.0 is default
                for d in parsed.sector_deltas.values()
            )
            if not has_explicit_delta:
                return FOLLOW_UP_TEMPLATES["missing_severity"]

        # All good
        return None

    def get_followup_options(self, parsed: ParsedScenario) -> list[str]:
        """Get quick-reply options for the follow-up question."""
        if not parsed.city:
            from engine.nl_engine.domain_maps import CITY_ALIASES
            cities = sorted(set(CITY_ALIASES.values()))
            return [c.replace("_", " ").title() for c in cities[:6]]

        active_sectors = [s for s, d in parsed.sector_deltas.items() if d != 0.0]
        if not active_sectors:
            return ["IT Boom", "Manufacturing Push", "Real Estate Crisis", "Agriculture Shock"]

        return ["Mild", "Moderate", "Severe"]

    def advance(self, user_response: str | None = None) -> ConversationState:
        """Advance conversation state based on current state and user input."""
        self.turn_count += 1

        if self.state == ConversationState.IDLE:
            self.state = ConversationState.PARSING
        elif self.state == ConversationState.NEEDS_INPUT:
            self.state = ConversationState.PARSING
        elif self.state == ConversationState.PARSING:
            self.state = ConversationState.CONFIRMED
        elif self.state == ConversationState.CONFIRMED:
            self.state = ConversationState.SIMULATING
        elif self.state == ConversationState.SIMULATING:
            self.state = ConversationState.DONE

        return self.state

    def reset(self) -> None:
        """Reset conversation state."""
        self.state = ConversationState.IDLE
        self.mode = ConversationMode.QUICK
        self.turn_count = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/unit/test_conversation.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nl_engine/conversation.py backend/tests/unit/test_conversation.py
git commit -m "feat(engine): add conversation state machine with mode detection"
```

---

## Task 7: Backend Models Update

**Files:**
- Modify: `backend/engine/models.py`

- [ ] **Step 1: Add GroupImpact model and new WS message types to models.py**

Add after the `CaseStudy` class (around line 112):

```python
class NeedsInputMessage(BaseModel):
    type: Literal["NEEDS_INPUT"] = "NEEDS_INPUT"
    question: str
    inferred_params: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=list)
    mode: str = "quick"


class InputResponseMessage(BaseModel):
    type: Literal["INPUT_RESPONSE"] = "INPUT_RESPONSE"
    text: str


class GroupScoresMessage(BaseModel):
    type: Literal["GROUP_SCORES"] = "GROUP_SCORES"
    groups: list[GroupImpact]
    citizen_satisfaction: int
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All PASS (no regressions)

- [ ] **Step 3: Commit**

```bash
git add backend/engine/models.py
git commit -m "feat(engine): add GroupImpact and new WS message models"
```

---

## Task 8: WebSocket Integration

**Files:**
- Modify: `backend/app/ws/simulation.py`

- [ ] **Step 1: Update simulation.py to use nl_engine router and add GROUP_SCORES**

Replace the full content of `backend/app/ws/simulation.py`:

```python
from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError

from app.config import settings
from app.db import get_db
from engine.models import (
    StartScenarioMessage,
    InputResponseMessage,
)
from engine.prediction_generator import generate_prediction
from engine.runner import run_simulation, SimulationTimeoutError
from engine.scenario_parser import ScenarioParseError, build_params, parse_scenario
from engine.tertiary_loop import synthesize_evidence
from engine.nl_engine.router import IntentRouter
from engine.nl_engine.conversation import ConversationManager, ConversationMode
from engine.nl_engine.group_scorer import score_groups, compute_satisfaction

logger = logging.getLogger(__name__)
router = APIRouter()

# Shared instances (stateless, safe to share)
_intent_router = IntentRouter()


@router.websocket("/ws/simulate")
async def simulation_websocket(websocket: WebSocket):
    await websocket.accept()
    simulation_id = str(uuid4())
    db = await get_db()
    conv = ConversationManager()

    try:
        data = await _receive_start(websocket)
        scenario_text = data.scenario

        # ── Parsing stage with conversation ──────────────────────────
        await _send_stage(websocket, "parsing", "Reading your scenario...")

        parsed, confidence = await _intent_router.route(scenario_text)
        conv.mode = conv.detect_mode(scenario_text)

        # If low confidence or incomplete params, ask follow-up
        followup = conv.get_followup(parsed)
        if followup and conv.mode == ConversationMode.QUICK:
            options = conv.get_followup_options(parsed)
            conv.state = "needs_input"
            await websocket.send_json({
                "type": "NEEDS_INPUT",
                "question": followup,
                "inferred_params": {
                    "city": parsed.city,
                    "sectors": [
                        {"name": s, "delta": d}
                        for s, d in parsed.sector_deltas.items()
                        if d != 0.0
                    ],
                },
                "options": options,
                "mode": conv.mode.value,
            })

            # Wait for user response
            response_data = await _receive_input_response(websocket)
            # Re-parse with the additional context
            combined_text = f"{scenario_text} {response_data.text}"
            parsed, confidence = await _intent_router.route(combined_text)

        # Ensure we have a city
        if not parsed.city:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "parsing",
                "code": "CLARIFICATION_NEEDED",
                "message": "I could not identify the city. Try naming one Indian city.",
            })
            return

        params = build_params(parsed)
        boundary = await db.get_region_boundary(params.city)
        if boundary is None:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "parsing",
                "code": "CITY_DATA_MISSING",
                "message": f"No boundary data found for {params.city}.",
            })
            return

        await websocket.send_json({"type": "PARSED", "params": parsed.model_dump(), "boundary": boundary})

        # ── Prediction stage ─────────────────────────────────────────
        await _send_stage(websocket, "predicting", "Generating a before-simulation expectation.")
        prediction = await generate_prediction(params)
        await websocket.send_json({"type": "PREDICTION", "prediction": prediction.model_dump()})

        # ── Simulation stage ─────────────────────────────────────────
        await _send_stage(websocket, "simulating", "Animating monthly H3 cell changes across the city.")
        deadline = asyncio.get_running_loop().time() + settings.sim_timeout_ms / 1000.0
        frames = []
        async for frame in run_simulation(params, boundary, db=db, deadline=deadline):
            frames.append(frame)
            await websocket.send_json({"type": "FRAME", "payload": frame})

        if not frames:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "simulating",
                "code": "NO_FRAMES",
                "message": "Simulation produced no frames.",
            })
            return

        final_frame = frames[-1]

        # ── Case studies stage ───────────────────────────────────────
        await _send_stage(websocket, "retrieving", "Finding Indian urban precedents.")
        case_studies = await db.search_case_studies(
            parsed.keywords, city=parsed.city, top_k=5,
        )
        await websocket.send_json({
            "type": "CASE_STUDIES",
            "studies": [case.model_dump() for case in case_studies],
        })

        # ── Group scoring stage (NEW) ────────────────────────────────
        await _send_stage(websocket, "synthesizing", "Computing social group impacts.")
        groups = score_groups(parsed.sector_deltas, final_frame["metrics"])
        satisfaction = compute_satisfaction(groups)
        await websocket.send_json({
            "type": "GROUP_SCORES",
            "groups": [g.to_dict() for g in groups],
            "citizen_satisfaction": satisfaction,
        })

        # ── Evidence stage ───────────────────────────────────────────
        evidence = synthesize_evidence(params, prediction, final_frame, case_studies)
        await websocket.send_json({"type": "EVIDENCE", "evidence": evidence})

        # ── Done ─────────────────────────────────────────────────────
        saved_id = await db.save_simulation(
            region_id=None,
            params=params.to_dict(),
            horizon_months=params.horizon_months,
            result_summary=final_frame["metrics"],
            cell_states=final_frame["cells"],
        )
        await websocket.send_json({"type": "DONE", "simulationId": saved_id or simulation_id})

    except ScenarioParseError as e:
        await websocket.send_json({
            "type": "ERROR",
            "stage": "parsing",
            "code": "CLARIFICATION_NEEDED",
            "message": str(e),
        })
    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "ERROR",
            "stage": "parsing",
            "code": "TIMEOUT",
            "message": "Did not receive message within 30 seconds.",
        })
    except SimulationTimeoutError:
        await websocket.send_json({
            "type": "ERROR",
            "stage": "simulating",
            "code": "TIMEOUT",
            "message": "Simulation exceeded the time limit.",
        })
    except Exception as e:
        logger.exception("Simulation %s failed", simulation_id)
        try:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "simulating",
                "code": "SIMULATION_FAILED",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def _receive_start(websocket: WebSocket) -> StartScenarioMessage:
    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
    try:
        payload = json.loads(message)
        return StartScenarioMessage(**payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ScenarioParseError(
            f"First message must be JSON: {{ type: 'START', scenario: '...' }}. {e}"
        ) from e


async def _receive_input_response(websocket: WebSocket) -> InputResponseMessage:
    message = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
    try:
        payload = json.loads(message)
        return InputResponseMessage(**payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ScenarioParseError(f"Invalid input response: {e}") from e


async def _send_stage(websocket: WebSocket, stage: str, message: str) -> None:
    await websocket.send_json({"type": "STAGE", "stage": stage, "message": message})
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/ws/simulation.py
git commit -m "feat(ws): integrate NL engine router and group scoring into WS pipeline"
```

---

## Task 9: Frontend Types Update

**Files:**
- Modify: `frontend/src/types/simulation.ts`

- [ ] **Step 1: Add new types to simulation.ts**

Add after the `WSDoneMessage` interface (around line 160):

```typescript
export interface GroupImpact {
  name: string;
  purchasing_power: number;
  income_stability: number;
  expense_pressure: number;
  housing_impact: number;
  employment_impact: number;
  severity: "low" | "moderate" | "high";
}

export interface WSNeedsInputMessage {
  type: "NEEDS_INPUT";
  question: string;
  inferred_params: {
    city: string;
    sectors: { name: string; delta: number }[];
  };
  options: string[];
  mode: "quick" | "deep";
}

export interface WSGroupScoresMessage {
  type: "GROUP_SCORES";
  groups: GroupImpact[];
  citizen_satisfaction: number;
}
```

Update the `WSMessage` union type (around line 162):

```typescript
export type WSMessage =
  | WSStageMessage
  | WSParsedMessage
  | WSPredictionMessage
  | WSFrameMessage
  | WSCaseStudiesMessage
  | WSEvidenceMessage
  | WSErrorMessage
  | WSDoneMessage
  | WSNeedsInputMessage
  | WSGroupScoresMessage;
```

Update `PipelineStage` to include the new stage:

```typescript
export type PipelineStage =
  | "idle"
  | "parsing"
  | "predicting"
  | "simulating"
  | "retrieving"
  | "synthesizing"
  | "group_scoring"
  | "done"
  | "error"
  | "needs_input";
```

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run type-check`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/simulation.ts
git commit -m "feat(types): add GroupImpact and new WS message types"
```

---

## Task 10: Frontend Store Update

**Files:**
- Modify: `frontend/src/store/simulationStore.ts`

- [ ] **Step 1: Add conversation and group scores state to store**

Add new state fields to the `SimulationStore` interface (after `simulationId`):

```typescript
  // Conversation state
  conversationMessages: ConversationMessage[];
  conversationMode: "quick" | "deep";
  pendingQuestion: WSNeedsInputMessage | null;
  groupScores: GroupImpact[];
  citizenSatisfaction: number | null;
```

Add the `ConversationMessage` interface before `SimulationStore`:

```typescript
export interface ConversationMessage {
  role: "user" | "system";
  text: string;
  timestamp: number;
}
```

Add new imports at the top:

```typescript
import type {
  AggregateMetrics,
  CaseStudy,
  EvidenceReport,
  GroupImpact,
  ParsedScenario,
  PipelineStage,
  Prediction,
  SimulationFrame,
  WSGroupScoresMessage,
  WSNeedsInputMessage,
} from "@/types/simulation";
```

Add new state defaults and actions:

```typescript
  // In the initial state:
  conversationMessages: [],
  conversationMode: "quick",
  pendingQuestion: null,
  groupScores: [],
  citizenSatisfaction: null,

  // New actions:
  addConversationMessage: (role: "user" | "system", text: string) =>
    set((state) => ({
      conversationMessages: [
        ...state.conversationMessages,
        { role, text, timestamp: Date.now() },
      ],
    })),

  setPendingQuestion: (question: WSNeedsInputMessage | null) =>
    set({ pendingQuestion: question }),

  setConversationMode: (mode: "quick" | "deep") =>
    set({ conversationMode: mode }),

  setGroupScores: (msg: WSGroupScoresMessage) =>
    set({
      groupScores: msg.groups,
      citizenSatisfaction: msg.citizen_satisfaction,
    }),
```

Update `resetRun` to clear new state:

```typescript
  resetRun: () =>
    set({
      // ... existing resets ...
      conversationMessages: [],
      pendingQuestion: null,
      groupScores: [],
      citizenSatisfaction: null,
    }),
```

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run type-check`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store/simulationStore.ts
git commit -m "feat(store): add conversation state and group scores"
```

---

## Task 11: Frontend WebSocket Update

**Files:**
- Modify: `frontend/src/lib/ws.ts`
- Modify: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Add new message handlers to ws.ts**

Add to the `WSCallbacks` interface:

```typescript
  onNeedsInput?: (msg: WSNeedsInputMessage) => void;
  onGroupScores?: (msg: WSGroupScoresMessage) => void;
```

Add imports:

```typescript
import type {
  WSCaseStudiesMessage,
  WSDoneMessage,
  WSErrorMessage,
  WSEvidenceMessage,
  WSFrameMessage,
  WSGroupScoresMessage,
  WSNeedsInputMessage,
  WSParsedMessage,
  WSPredictionMessage,
  WSStageMessage,
  WSMessage,
} from "@/types/simulation";
```

Add cases to `handleMessage`:

```typescript
      case "NEEDS_INPUT":
        this.callbacks.onNeedsInput?.(data);
        break;
      case "GROUP_SCORES":
        this.callbacks.onGroupScores?.(data);
        break;
```

Add a method to send input responses:

```typescript
  sendInputResponse(text: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "INPUT_RESPONSE", text }));
    }
  }
```

- [ ] **Step 2: Update useWebSocket.ts to wire new callbacks**

Update the callback setup in `startSimulation`:

```typescript
        onNeedsInput: (msg) => {
          const store = useSimulationStore.getState();
          store.setPendingQuestion(msg);
          store.addConversationMessage("system", msg.question);
        },
        onGroupScores: (msg) => useSimulationStore.getState().setGroupScores(msg),
```

Add a `sendResponse` function to the hook return:

```typescript
  const sendResponse = useCallback((text: string) => {
    const store = useSimulationStore.getState();
    store.addConversationMessage("user", text);
    store.setPendingQuestion(null);
    clientRef.current?.sendInputResponse(text);
  }, []);

  return { startSimulation, stopSimulation, sendResponse };
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run type-check`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/ws.ts frontend/src/hooks/useWebSocket.ts
git commit -m "feat(ws): add NEEDS_INPUT and GROUP_SCORES message handling"
```

---

## Task 12: Conversation Panel (Frontend)

**Files:**
- Create: `frontend/src/components/controls/ConversationPanel.tsx`
- Modify: `frontend/src/app/page.tsx` (replace ScenarioPanel import)

- [ ] **Step 1: Create ConversationPanel.tsx**

```tsx
"use client";

import { useRef, useEffect } from "react";
import { useSimulationStore, type ConversationMessage } from "@/store/simulationStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { SECTOR_LABELS } from "@/types/simulation";
import { PresetSelector } from "./PresetSelector";

const QUICK_EXAMPLES = [
  "What if petrol prices spike in Mumbai?",
  "What happens when there's a tech boom in Bengaluru?",
  "Heavy rainfall devastates Chennai — what changes?",
  "What if interest rates rise sharply across India?",
];

export function ConversationPanel() {
  const scenarioText = useSimulationStore((s) => s.scenarioText);
  const setScenarioText = useSimulationStore((s) => s.setScenarioText);
  const parsed = useSimulationStore((s) => s.parsedScenario);
  const pipelineStage = useSimulationStore((s) => s.pipelineStage);
  const error = useSimulationStore((s) => s.error);
  const messages = useSimulationStore((s) => s.conversationMessages);
  const pendingQuestion = useSimulationStore((s) => s.pendingQuestion);
  const conversationMode = useSimulationStore((s) => s.conversationMode);
  const setConversationMode = useSimulationStore((s) => s.setConversationMode);
  const resetAll = useSimulationStore((s) => s.resetAll);
  const { startSimulation, stopSimulation, sendResponse } = useWebSocket();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isRunning = !["idle", "done", "error", "needs_input"].includes(pipelineStage);
  const canRun = scenarioText.trim().length >= 4 && !isRunning;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleRun = () => {
    if (!canRun) return;
    const store = useSimulationStore.getState();
    store.addConversationMessage("user", scenarioText);
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/simulate";
    startSimulation(scenarioText, wsUrl);
  };

  const handleQuickReply = (option: string) => {
    sendResponse(option);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (pendingQuestion) {
        const input = (e.target as HTMLTextAreaElement).value.trim();
        if (input) {
          sendResponse(input);
          setScenarioText("");
        }
      } else if (canRun) {
        handleRun();
      }
    }
  };

  return (
    <aside className="w-[360px] bg-dark-200/95 border-r border-dark-100/50 h-full overflow-y-auto flex flex-col backdrop-blur-md shadow-2xl">
      {/* Header */}
      <div className="p-5 border-b border-dark-100/40 bg-dark-300/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-blue-600 flex items-center justify-center font-bold text-xs shadow-md shadow-blue-500/20 text-white">
              M
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-100 uppercase tracking-widest font-sans">
                MetroPulse
              </h1>
              <p className="text-[10px] text-gray-500 uppercase font-medium tracking-wider">
                What If? Simulator
              </p>
            </div>
          </div>
          {/* Mode Toggle */}
          <div className="flex rounded-lg border border-dark-100/60 overflow-hidden text-[9px] font-bold">
            <button
              onClick={() => setConversationMode("quick")}
              className={`px-2.5 py-1 transition-all ${
                conversationMode === "quick"
                  ? "bg-blue-600 text-white"
                  : "bg-dark-300/50 text-gray-500 hover:text-gray-300"
              }`}
            >
              What If?
            </button>
            <button
              onClick={() => setConversationMode("deep")}
              className={`px-2.5 py-1 transition-all ${
                conversationMode === "deep"
                  ? "bg-blue-600 text-white"
                  : "bg-dark-300/50 text-gray-500 hover:text-gray-300"
              }`}
            >
              Talk Numbers
            </button>
          </div>
        </div>
      </div>

      {/* Presets */}
      <div className="px-5 pt-4">
        <PresetSelector />
      </div>

      {/* Conversation Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
              Try a scenario
            </p>
            {QUICK_EXAMPLES.map((example) => (
              <button
                key={example}
                onClick={() => setScenarioText(example)}
                className="block w-full rounded-xl border border-dark-100/40 bg-dark-300/35 px-3 py-2.5 text-left text-xs text-gray-400 hover:border-blue-500/40 hover:text-gray-200 hover:bg-dark-300/60 transition-all duration-200"
              >
                {example}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} />
        ))}

        {/* Quick Reply Buttons */}
        {pendingQuestion && pendingQuestion.options.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pl-8">
            {pendingQuestion.options.map((option) => (
              <button
                key={option}
                onClick={() => handleQuickReply(option)}
                className="rounded-lg border border-blue-500/30 bg-blue-950/40 px-3 py-1.5 text-[11px] font-medium text-blue-300 hover:bg-blue-900/50 hover:border-blue-400/50 transition-all"
              >
                {option}
              </button>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-dark-100/40 bg-dark-300/30">
        {pendingQuestion ? (
          <div className="space-y-2">
            <textarea
              value={scenarioText}
              onChange={(e) => setScenarioText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Type your answer..."
              className="w-full resize-none rounded-xl border border-dark-100/70 bg-dark-300/60 px-3.5 py-3 text-xs leading-relaxed text-gray-200 outline-none focus:border-blue-500/70 transition-all"
            />
            <button
              onClick={() => {
                sendResponse(scenarioText);
                setScenarioText("");
              }}
              className="w-full rounded-xl bg-blue-600 py-2 text-xs font-bold text-white hover:bg-blue-500 transition-all"
            >
              Send
            </button>
          </div>
        ) : (
          <>
            <textarea
              value={scenarioText}
              onChange={(e) => setScenarioText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              placeholder={conversationMode === "quick" ? "What if...?" : "Set manufacturing -23%, SEZ policy, Chennai, 36 months"}
              className="w-full resize-none rounded-xl border border-dark-100/70 bg-dark-300/60 px-3.5 py-3 text-xs leading-relaxed text-gray-200 outline-none focus:border-blue-500/70 transition-all"
            />
            <div className="flex gap-2 pt-2">
              {isRunning ? (
                <button
                  onClick={stopSimulation}
                  className="flex-1 rounded-xl bg-red-600 hover:bg-red-500 py-2.5 text-xs font-bold text-white transition-all active:scale-95"
                >
                  Stop
                </button>
              ) : (
                <button
                  disabled={!canRun}
                  onClick={handleRun}
                  className={`flex-1 rounded-xl py-2.5 text-xs font-bold transition-all active:scale-95 ${
                    canRun
                      ? "bg-blue-600 text-white hover:bg-blue-500"
                      : "bg-dark-300 text-gray-600 cursor-not-allowed"
                  }`}
                >
                  Run Simulation
                </button>
              )}
              <button
                onClick={resetAll}
                className="rounded-xl border border-dark-100/80 bg-dark-300/50 px-4 py-2.5 text-xs font-semibold text-gray-400 hover:text-gray-200 transition-all active:scale-95"
              >
                Reset
              </button>
            </div>
          </>
        )}

        {error && (
          <div className="mt-2 rounded-xl border border-red-800 bg-red-950/30 px-3.5 py-3 text-xs text-red-300">
            {error}
          </div>
        )}
      </div>

      {/* Parsed Params HUD */}
      {parsed && (
        <div className="px-5 pb-4">
          <ParsedParamsHUD parsed={parsed} />
        </div>
      )}
    </aside>
  );
}

function ChatBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
          isUser
            ? "bg-blue-600/80 text-white rounded-br-md"
            : "bg-dark-300/70 text-gray-300 rounded-bl-md border border-dark-100/40"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}

function ParsedParamsHUD({ parsed }: { parsed: NonNullable<ReturnType<typeof useSimulationStore.getState>["parsedScenario"]> }) {
  const deltas = Object.entries(parsed.sector_deltas).filter(([, v]) => Math.abs(v) > 0);
  return (
    <section className="space-y-2 rounded-xl border border-dark-100/50 bg-dark-300/50 p-3 text-[10px]">
      <div className="font-bold text-blue-400 uppercase tracking-widest">
        {parsed.city.replace("_", " ")} &middot; {parsed.horizon_months}mo
      </div>
      {deltas.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {deltas.map(([sector, value]) => (
            <span
              key={sector}
              className={`rounded px-1.5 py-0.5 font-semibold ${
                value >= 0
                  ? "bg-emerald-950/50 text-emerald-300"
                  : "bg-red-950/50 text-red-300"
              }`}
            >
              {SECTOR_LABELS[sector] ?? sector} {value > 0 ? "+" : ""}
              {value}%
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Update page.tsx to use ConversationPanel**

In `frontend/src/app/page.tsx`, replace:
```typescript
import { ScenarioPanel } from "@/components/controls/ScenarioPanel";
```
with:
```typescript
import { ConversationPanel } from "@/components/controls/ConversationPanel";
```

And replace `<ScenarioPanel />` with `<ConversationPanel />`.

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run type-check && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/controls/ConversationPanel.tsx frontend/src/app/page.tsx
git commit -m "feat(ui): add ConversationPanel with chat-like what-if interface"
```

---

## Task 13: Group Impact Panel (Frontend)

**Files:**
- Create: `frontend/src/components/dashboard/GroupImpactPanel.tsx`

- [ ] **Step 1: Create GroupImpactPanel.tsx**

```tsx
"use client";

import React from "react";
import { useSimulationStore } from "@/store/simulationStore";
import type { GroupImpact } from "@/types/simulation";

const GROUP_LABELS: Record<string, string> = {
  farmers: "Farmers",
  students: "Students",
  middle_class_families: "Middle Class",
  small_businesses: "Small Business",
  corporates: "Corporates",
  transport_sector: "Transport",
  government: "Government",
};

const GROUP_ICONS: Record<string, string> = {
  farmers: "🌾",
  students: "🎓",
  middle_class_families: "🏠",
  small_businesses: "🏪",
  corporates: "🏢",
  transport_sector: "🚛",
  government: "🏛️",
};

const SEVERITY_COLORS = {
  low: "border-emerald-500/30 bg-emerald-950/20 text-emerald-300",
  moderate: "border-amber-500/30 bg-amber-950/20 text-amber-300",
  high: "border-red-500/30 bg-red-950/20 text-red-300",
};

export const GroupImpactPanel = React.memo(function GroupImpactPanel() {
  const groupScores = useSimulationStore((s) => s.groupScores);
  const citizenSatisfaction = useSimulationStore((s) => s.citizenSatisfaction);

  if (groupScores.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Citizen Satisfaction Gauge */}
      {citizenSatisfaction !== null && (
        <div className="rounded-xl border border-dark-100/50 bg-dark-200/80 p-4 backdrop-blur-md">
          <div className="text-[9px] font-bold uppercase tracking-widest text-gray-500 mb-2">
            Citizen Satisfaction
          </div>
          <div className="flex items-center gap-3">
            <div className="text-3xl font-bold text-white">
              {citizenSatisfaction}
            </div>
            <div className="flex-1">
              <div className="h-2 rounded-full bg-dark-300 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    citizenSatisfaction >= 60
                      ? "bg-emerald-500"
                      : citizenSatisfaction >= 40
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${citizenSatisfaction}%` }}
                />
              </div>
              <div className="flex justify-between text-[9px] text-gray-600 mt-1">
                <span>0</span>
                <span>100</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Group Cards */}
      <div className="grid grid-cols-2 gap-2">
        {groupScores.map((group) => (
          <GroupCard key={group.name} group={group} />
        ))}
      </div>
    </div>
  );
});

function GroupCard({ group }: { group: GroupImpact }) {
  const label = GROUP_LABELS[group.name] ?? group.name;
  const icon = GROUP_ICONS[group.name] ?? "📊";
  const colorClass = SEVERITY_COLORS[group.severity];

  return (
    <div className={`rounded-xl border p-3 backdrop-blur-md ${colorClass}`}>
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-sm">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider">{label}</span>
      </div>
      <div className="space-y-1 text-[10px]">
        <MetricRow label="Purchasing Power" value={group.purchasing_power} />
        <MetricRow label="Income" value={group.income_stability} />
        <MetricRow label="Expenses" value={group.expense_pressure} inverted />
        <MetricRow label="Housing" value={group.housing_impact} />
        <MetricRow label="Jobs" value={-group.employment_impact} />
      </div>
    </div>
  );
}

function MetricRow({
  label,
  value,
  inverted = false,
}: {
  label: string;
  value: number;
  inverted?: boolean;
}) {
  const isPositive = inverted ? value < 0 : value > 0;
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-500">{label}</span>
      <span className={`font-mono font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
        {value > 0 ? "+" : ""}
        {value.toFixed(1)}%
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Integrate GroupImpactPanel into page.tsx**

Import and render `<GroupImpactPanel />` in the right sidebar or bottom drawer of `page.tsx`, next to the existing `EvidencePanel`.

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run type-check && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/GroupImpactPanel.tsx frontend/src/app/page.tsx
git commit -m "feat(ui): add GroupImpactPanel with social group cards"
```

---

## Task 14: Pipeline Flow Update

**Files:**
- Modify: `frontend/src/components/dashboard/PipelineFlow.tsx`

- [ ] **Step 1: Add "Social Impact" stage to PipelineFlow**

Update the STEPS array:

```typescript
const STEPS: { stage: PipelineStage; label: string }[] = [
  { stage: "parsing", label: "Prompt" },
  { stage: "predicting", label: "Prediction" },
  { stage: "simulating", label: "Simulation" },
  { stage: "retrieving", label: "Evidence" },
  { stage: "synthesizing", label: "Social Impact" },
  { stage: "group_scoring", label: "Groups" },
];
```

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run type-check`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/PipelineFlow.tsx
git commit -m "feat(ui): add Social Impact stage to pipeline flow"
```

---

## Task 15: Ollama Parser (Optional)

**Files:**
- Create: `backend/engine/nl_engine/ollama_parser.py`

- [ ] **Step 1: Implement ollama_parser.py**

```python
# backend/engine/nl_engine/ollama_parser.py
"""Path 3: Local LLM fallback via Ollama (optional)."""
from __future__ import annotations

import json
import logging
from typing import Any

from engine.models import ParsedScenario, SECTOR_NAMES
from engine.nl_engine.domain_maps import CITY_ALIASES, SECTOR_SYNONYMS

logger = logging.getLogger(__name__)

PARSER_PROMPT = """You are an economic scenario parser. Given a user's text, extract structured parameters.

User text: "{text}"

Extract as JSON:
{{
  "city": "city name or null",
  "sectors": [
    {{"name": "sector_name", "delta": number}}
  ],
  "policies": ["policy_name"],
  "events": ["event_name"],
  "horizon_months": number
}}

Valid sectors: it_ites, manufacturing, real_estate, trade_hospitality, transport_logistics, informal, public_admin
Valid policies: sez, smart_city, amrut, rera, pm_awas, make_in_india, digital_india
Valid events: fuel_price_hike, heavy_rainfall, drought, interest_rate_hike, subsidy_added, unemployment_rise, pandemic

Respond with only the JSON object."""


class OllamaParser:
    """Ollama-based parser for complex/ambiguous inputs."""

    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url

    async def parse(self, text: str) -> ParsedScenario:
        """Parse text using local Ollama model. Falls back to empty result if unavailable."""
        try:
            response = await self._call_ollama(text)
            return self._parse_response(response, text)
        except Exception as e:
            logger.warning("Ollama parse failed: %s", e)
            return self._fallback_result(text)

    async def _call_ollama(self, text: str) -> str:
        """Call Ollama API. Raises if not available."""
        import httpx

        prompt = PARSER_PROMPT.format(text=text)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    def _parse_response(self, response: str, original_text: str) -> ParsedScenario:
        """Parse Ollama JSON response into ParsedScenario."""
        try:
            # Extract JSON from response (may have markdown fences)
            json_str = response
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse Ollama response as JSON")
            return self._fallback_result(original_text)

        # Normalize city
        city_raw = (data.get("city") or "").lower().strip()
        city = CITY_ALIASES.get(city_raw, city_raw if city_raw else "")

        # Build sector deltas
        sector_deltas = {s: 0.0 for s in SECTOR_NAMES}
        for sector_info in data.get("sectors", []):
            name = sector_info.get("name", "")
            delta = float(sector_info.get("delta", 0))
            if name in SECTOR_NAMES:
                sector_deltas[name] = max(-50.0, min(50.0, delta))

        # Policies
        policies = data.get("policies", [])

        # Horizon
        horizon = int(data.get("horizon_months", 24))
        horizon = min([6, 12, 24, 60], key=lambda x: abs(x - horizon))

        keywords = [city] + [s for s, d in sector_deltas.items() if d != 0] + policies

        return ParsedScenario(
            city=city,
            sector_deltas=sector_deltas,
            policies_active=policies,
            public_works_zone=None,
            horizon_months=horizon,
            causal_chain=original_text.strip(),
            keywords=[k for k in keywords if k],
            confidence="medium",
            assumptions=["Parsed via local LLM. Verify parameters."],
        )

    def _fallback_result(self, text: str) -> ParsedScenario:
        """Return empty result when Ollama is unavailable."""
        return ParsedScenario(
            city="",
            sector_deltas={s: 0.0 for s in SECTOR_NAMES},
            policies_active=[],
            public_works_zone=None,
            horizon_months=24,
            causal_chain=text.strip(),
            keywords=[],
            confidence="low",
            assumptions=["Could not parse scenario. Please try rephrasing."],
        )
```

- [ ] **Step 2: Verify backend tests still pass**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add backend/engine/nl_engine/ollama_parser.py
git commit -m "feat(engine): add optional Ollama parser for complex inputs"
```

---

## Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm run test`
Expected: All PASS

- [ ] **Step 4: Manual E2E test**

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser, type "What if petrol prices spike in Mumbai?"
4. Verify: conversation panel shows chat bubbles, follow-up question appears, simulation runs, group impact cards show

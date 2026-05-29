"""Shared knowledge backbone for all NLP parsing paths."""
from __future__ import annotations

import re

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
    "it": "it_ites", "digital": "it_ites",
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
        "real_estate": +0.10,
        "manufacturing": +0.06,
        "informal": +0.04,
    },
    "global_recession": {
        "it_ites": -0.20,
        "manufacturing": -0.15,
        "trade_hospitality": -0.10,
        "real_estate": -0.08,
    },
    "fuel_import_stop": {
        "transport_logistics": -0.25,
        "manufacturing": -0.12,
        "informal": -0.15,
        "trade_hospitality": -0.10,
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
    "fuel_import_stop": [
        "stop importing petrol", "fuel import ban", "petrol embargo",
        "fuel shortage", "oil import ban", "stopped importing",
        "fuel import stop", "oil embargo",
    ],
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

# Scale factors for cause-effect chain deltas based on intensity words.
# When a user says "petrol prices spike" vs "petrol prices increase slightly",
# the base event deltas should scale accordingly.
EVENT_SCALE_MAP: dict[str, float] = {
    "extreme": 2.0,   # "spike", "crash", "skyrocketed", "collapse"
    "strong": 1.5,    # "surge", "plummet", "sharp rise", "major drop"
    "moderate": 1.0,  # "increase", "decline", "rise", "drop" (default)
    "mild": 0.5,      # "slight", "minor", "gradual", "dip"
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

# ── Policy keywords ────────────────────────────────────────────────────────

POLICY_KEYWORDS: dict[str, list[str]] = {
    "SEZ Notification": ["sez", "special economic zone"],
    "Smart City Mission": ["smart city"],
    "AMRUT": ["amrut", "water", "sanitation"],
    "RERA Compliance": ["rera"],
    "PM Awas Yojana": ["pmay", "awas", "affordable housing", "housing scheme"],
    "Make in India": ["make in india"],
    "Digital India": ["digital india"],
}

# ── Direction words (positive / negative) ──────────────────────────────────

NEGATIVE_WORDS: list[str] = [
    "drop", "drops", "dropped", "dropping", "decline", "declines", "declined",
    "falls", "fall", "fallen", "falling", "cut", "cuts", "cutting",
    "loss", "crisis", "shock", "shocks", "shocked",
    "reduce", "reduces", "reduced", "reducing",
    "devastate", "devastates", "devastated", "devastating",
    "crash", "crashes", "crashed", "crashing",
    "plummet", "plummets", "plummeted",
    "slump", "slumps", "slumped",
    "destroyed", "destroy", "destroys", "destroying",
    "ruin", "ruins", "ruined",
    "damage", "damages", "damaged",
    # Cessation / stop words
    "stop", "stops", "stopped", "stopping",
    "halt", "halts", "halted",
    "ban", "bans", "banned",
    "cease", "ceased",
    "embargo", "suspend", "suspended",
    "disrupt", "disrupted", "shutdown", "shut",
]

POSITIVE_WORDS: list[str] = [
    "increase", "increases", "increased", "increasing",
    "rise", "rises", "risen", "rising",
    "boom", "growth", "boost", "boosted",
    "push", "pushed", "pushing",
    "investment", "invested", "investing",
    "improve", "improved", "improving",
    "surge", "surges", "surged", "surging",
    "soar", "soars", "soared", "soaring",
    "gain", "gains", "gained", "gaining",
    "grows", "grew", "growing",
]


# ── Default delta magnitude ────────────────────────────────────────────────

DEFAULT_DELTA: float = 15.0


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


def get_event_scale(text: str) -> float:
    """Detect intensity modifiers in text and return a scale factor for event deltas.

    Returns a multiplier: extreme=2.0, strong=1.5, moderate=1.0, mild=0.5.
    Used to scale cause-effect chain base deltas based on how strong the user's
    wording is (e.g., "petrol prices spike" → 2.0x, "slight fuel increase" → 0.5x).
    """
    lowered = text.lower()
    for level in ("extreme", "strong", "mild", "moderate"):
        if any(w in lowered for w in SENTIMENT_WORDS["negative"][level]):
            return EVENT_SCALE_MAP[level]
        if any(w in lowered for w in SENTIMENT_WORDS["positive"][level]):
            return EVENT_SCALE_MAP[level]
    return 1.0  # moderate default — no scaling


def has_word_boundary_match(text: str, words: list[str]) -> bool:
    """Check if any word from the list appears as a whole word in text."""
    for w in words:
        if re.search(r'\b' + re.escape(w) + r'\b', text):
            return True
    return False

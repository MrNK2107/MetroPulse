"""Path 1: Enhanced regex parser with domain knowledge integration."""
from __future__ import annotations

import re

from engine.models import ParsedScenario, SECTOR_NAMES
from engine.nl_engine.domain_maps import (
    CITY_ALIASES,
    SECTOR_SYNONYMS,
    CAUSE_EFFECT_CHAINS,
    detect_event,
    detect_sentiment,
)

# Policy keywords
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

    def __init__(self) -> None:
        self.last_confidence: float = 0.0

    def parse(self, text: str) -> ParsedScenario:
        lowered = text.lower()

        # Extract city
        city = self._extract_city(lowered)

        # Extract sector deltas via synonyms + explicit percentages
        sector_deltas = {s: 0.0 for s in SECTOR_NAMES}
        mentioned_sectors: list[str] = []
        for word in lowered.split():
            # Check synonyms first, then canonical sector names
            sector = SECTOR_SYNONYMS.get(word)
            if sector is None and word in SECTOR_NAMES:
                sector = word
            if sector and sector not in mentioned_sectors:
                mentioned_sectors.append(sector)

        # Also check multi-word synonyms
        for synonym, sector in SECTOR_SYNONYMS.items():
            if " " in synonym and synonym in lowered and sector not in mentioned_sectors:
                mentioned_sectors.append(sector)

        # Extract explicit percentages
        percent_match = re.search(r"([+-]?\d{1,3})\s*%", lowered)
        explicit_delta = float(percent_match.group(1)) if percent_match else None

        # Also check "increased by N%" format
        if explicit_delta is None:
            inc_match = re.search(r"increased by\s*(\d{1,3})\s*%", lowered)
            if inc_match:
                explicit_delta = float(inc_match.group(1))

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
        numeric_confidence = self._compute_confidence(city, mentioned_sectors, explicit_delta)
        self.last_confidence = numeric_confidence
        if numeric_confidence >= 0.7:
            confidence_label = "high"
        elif numeric_confidence >= 0.4:
            confidence_label = "medium"
        else:
            confidence_label = "low"

        keywords = [city, *mentioned_sectors, *policies] if city else [*mentioned_sectors, *policies]

        return ParsedScenario(
            city=city or "",
            sector_deltas=sector_deltas,
            policies_active=policies,
            public_works_zone=None,
            horizon_months=horizon,
            causal_chain=text.strip(),
            keywords=[k for k in keywords if k],
            confidence=confidence_label,
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
        match = re.search(r"(\d{1,2})\s*(?:month|months)\b", text)
        if match:
            value = int(match.group(1))
            return min([6, 12, 24, 60], key=lambda x: abs(x - value))
        match = re.search(r"(\d)\s*(?:year|years|yr|yrs)\b", text)
        if match:
            value = int(match.group(1)) * 12
            return min([6, 12, 24, 60], key=lambda x: abs(x - value))
        return 24

    def _compute_confidence(
        self, city: str | None, sectors: list[str], explicit_delta: float | None
    ) -> float:
        score = 0.0
        if city:
            score += 0.4
        if sectors:
            score += 0.3
        if explicit_delta is not None:
            score += 0.2
        return min(score, 1.0)

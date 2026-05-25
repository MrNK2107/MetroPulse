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
    POLICY_KEYWORDS,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    detect_event,
    detect_sentiment,
)

# Magnitude adjectives mapped to delta values
MAGNITUDE_ADJECTIVES: dict[str, float] = {
    "skyrocketed": 40, "surged": 35, "exploded": 40, "crashed": -40,
    "devastating": -35, "plummeted": -35, "collapse": -40,
    "significant": 25, "major": 25, "sharp": 25, "soared": 30,
    "slight": 8, "minor": 8, "gradual": 8, "mild": 8,
    "moderate": 15, "steady": 12,
}


def _fuzzy_match_city(text: str, threshold: float = 0.75) -> str | None:
    """Fuzzy match a city name with SequenceMatcher ratio."""
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
        sectors_found = self._extract_sectors(doc)

        # Delta extraction via NUM entities + context
        explicit_delta = self._extract_delta(doc)

        # Event detection
        event = detect_event(text)

        # Build sector deltas
        sector_deltas: dict[str, float] = {s: 0.0 for s in SECTOR_NAMES}
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
                sector_deltas["manufacturing"] = (
                    (magnitude * 0.6) if direction == "positive" else -(magnitude * 0.6)
                )
                mentioned_sectors = ["it_ites", "manufacturing"]

        # Policy detection
        lowered = text.lower()
        policies = [
            policy
            for policy, keywords in POLICY_KEYWORDS.items()
            if any(kw in lowered for kw in keywords)
        ]

        # Confidence scoring
        confidence_score = self._compute_confidence_score(city, mentioned_sectors, explicit_delta)

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
        # Try GPE and ORG entities (spaCy sometimes tags Indian cities as ORG)
        for ent in doc.ents:
            if ent.label_ in ("GPE", "ORG"):
                city_id = CITY_ALIASES.get(ent.text.lower())
                if city_id:
                    return city_id
                # Fuzzy match
                city_id = _fuzzy_match_city(ent.text)
                if city_id:
                    return city_id

        # Fallback: check tokens against aliases
        for token in doc:
            if token.is_alpha and len(token.text) > 3:
                city_id = CITY_ALIASES.get(token.text.lower())
                if city_id:
                    return city_id

        return None

    def _extract_sectors(self, doc: Any) -> list[str]:
        sectors: set[str] = set()

        # Check noun phrases against synonyms
        for chunk in doc.noun_chunks:
            chunk_lower = chunk.text.lower()
            for synonym, sector in SECTOR_SYNONYMS.items():
                if synonym in chunk_lower:
                    sectors.add(sector)

        # Check individual tokens against synonyms AND canonical names
        for token in doc:
            if token.is_alpha:
                sector = SECTOR_SYNONYMS.get(token.text.lower())
                if sector:
                    sectors.add(sector)
                elif token.text.lower() in SECTOR_NAMES:
                    sectors.add(token.text.lower())

        return list(sectors)

    def _extract_delta(self, doc: Any) -> float | None:
        # Check PERCENT entities
        for ent in doc.ents:
            if ent.label_ == "PERCENT":
                num_text = ent.text.replace("%", "").strip()
                try:
                    return float(num_text)
                except ValueError:
                    pass

        # Check NUM entities that look like percentages
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
        if any(w in lowered for w in NEGATIVE_WORDS):
            return -abs(magnitude)
        if any(w in lowered for w in POSITIVE_WORDS):
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

    def _compute_confidence_score(
        self, city: str | None, sectors: list[str], delta: float | None
    ) -> str:
        score = 0.0
        if city:
            score += 0.3
        if sectors:
            score += 0.4 * min(len(sectors) / 3, 1.0)
        if delta is not None:
            score += 0.2
        # base 0.1 for having any text
        score += 0.1
        if score >= 0.7:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"

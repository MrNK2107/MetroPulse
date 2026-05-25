"""Intent router: dispatches to cheapest parser that can handle input."""
from __future__ import annotations

import logging

from engine.models import ParsedScenario
from engine.nl_engine.regex_parser import RegexParser

logger = logging.getLogger(__name__)

REGEX_CONFIDENCE_THRESHOLD = 0.8
SPACY_CONFIDENCE_THRESHOLD = 0.6


class IntentRouter:
    """Three-path intent router: regex -> spaCy -> Ollama fallback."""

    def __init__(self) -> None:
        self._regex = RegexParser()
        self._spacy = None

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
        regex_confidence = self._confidence_score(regex_result, self._regex)
        if regex_confidence >= REGEX_CONFIDENCE_THRESHOLD:
            logger.debug("Router: regex path (confidence=%.2f)", regex_confidence)
            return regex_result, regex_confidence

        # Path 2: spaCy (fast local NLP)
        try:
            spacy_result = self.spacy.parse(text)
            spacy_confidence = self._confidence_score(spacy_result, self.spacy)
            if spacy_confidence >= SPACY_CONFIDENCE_THRESHOLD:
                logger.debug("Router: spaCy path (confidence=%.2f)", spacy_confidence)
                return spacy_result, spacy_confidence
        except RuntimeError:
            logger.warning("spaCy not available, skipping Path 2")

        # Path 3: Return best of regex/spaCy with warning
        if regex_confidence >= spacy_confidence:
            logger.debug("Router: returning regex result (low confidence=%.2f)", regex_confidence)
            return regex_result, regex_confidence
        logger.debug("Router: returning spaCy result (low confidence=%.2f)", spacy_confidence)
        return spacy_result, spacy_confidence

    def _confidence_score(self, parsed: ParsedScenario, parser=None) -> float:
        """Compute numeric confidence from parsed scenario."""
        # Use parser's own numeric confidence if available
        if parser is not None and hasattr(parser, 'last_confidence'):
            return parser.last_confidence

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

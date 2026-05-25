"""Conversation state machine for 'what if?' dialogue."""
from __future__ import annotations

import re
from enum import Enum

from engine.models import ParsedScenario
from engine.nl_engine.domain_maps import FOLLOW_UP_TEMPLATES, CITY_ALIASES


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
        has_numbers = bool(re.search(r"\d+%?", text))
        has_mode_keywords = any(
            w in text.lower() for w in ["deep mode", "talk numbers", "precise"]
        )

        if has_numbers or has_mode_keywords:
            return ConversationMode.DEEP

        has_vague_language = any(
            w in text.lower()
            for w in ["what if", "imagine", "suppose", "happens", "affect", "impact"]
        )
        if has_vague_language:
            return ConversationMode.QUICK

        return ConversationMode.QUICK

    def get_followup(self, parsed: ParsedScenario) -> str | None:
        """Generate a follow-up question if params are incomplete. Returns None if complete."""
        if not parsed.city:
            return FOLLOW_UP_TEMPLATES["missing_city"]

        active_sectors = [s for s, d in parsed.sector_deltas.items() if d != 0.0]
        if not active_sectors:
            return FOLLOW_UP_TEMPLATES["missing_sector"]

        if parsed.confidence == "medium":
            has_explicit_delta = any(
                abs(d) > 0 and abs(d) != 15.0
                for d in parsed.sector_deltas.values()
            )
            if not has_explicit_delta:
                return FOLLOW_UP_TEMPLATES["missing_severity"]

        return None

    def get_followup_options(self, parsed: ParsedScenario) -> list[str]:
        """Get quick-reply options for the follow-up question."""
        if not parsed.city:
            cities = sorted(set(CITY_ALIASES.values()))
            return [c.replace("_", " ").title() for c in cities[:6]]

        active_sectors = [s for s, d in parsed.sector_deltas.items() if d != 0.0]
        if not active_sectors:
            return ["IT Boom", "Manufacturing Push", "Real Estate Crisis", "Agriculture Shock"]

        return ["Mild", "Moderate", "Severe"]

    def advance(self, user_response: str | None = None) -> ConversationState:
        """Advance conversation state."""
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

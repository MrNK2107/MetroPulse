import pytest
from engine.nl_engine.conversation import ConversationManager, ConversationMode
from engine.models import ParsedScenario


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
    parsed = ParsedScenario(
        city="",
        sector_deltas={"it_ites": 25.0, "manufacturing": 0.0, "real_estate": 0.0,
                       "trade_hospitality": 0.0, "transport_logistics": 0.0,
                       "informal": 0.0, "public_admin": 0.0},
        confidence="low",
    )
    question = mgr.get_followup(parsed)
    assert question is not None
    assert "city" in question.lower() or "which" in question.lower()


def test_no_followup_when_complete():
    mgr = ConversationManager()
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
    parsed = ParsedScenario(
        city="mumbai",
        sector_deltas={"it_ites": 0.0, "manufacturing": 0.0, "real_estate": 0.0,
                       "trade_hospitality": 0.0, "transport_logistics": 0.0,
                       "informal": 0.0, "public_admin": 0.0},
        horizon_months=24,
        confidence="medium",
    )
    question = mgr.get_followup(parsed)
    assert question is not None

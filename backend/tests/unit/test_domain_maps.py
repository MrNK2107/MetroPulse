"""Tests for domain_maps knowledge backbone."""
from engine.nl_engine.domain_maps import (
    SECTOR_SYNONYMS,
    CITY_ALIASES,
    CAUSE_EFFECT_CHAINS,
    SOCIAL_GROUPS,
    SENTIMENT_WORDS,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    EVENT_KEYWORDS,
    resolve_sector,
    resolve_city,
    get_event_effects,
    has_word_boundary_match,
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


def test_fuel_import_stop_event_exists():
    effects = get_event_effects("fuel_import_stop")
    assert effects["transport_logistics"] < 0
    assert effects["manufacturing"] < 0
    assert effects["informal"] < 0
    assert effects["trade_hospitality"] < 0


def test_fuel_import_stop_keywords_exist():
    keywords = EVENT_KEYWORDS["fuel_import_stop"]
    assert any("petrol" in kw for kw in keywords)
    assert any("import" in kw for kw in keywords)


def test_cessation_words_in_negative():
    for word in ("stopped", "halt", "ban", "banned", "cease", "embargo", "suspended"):
        assert word in NEGATIVE_WORDS, f"'{word}' missing from NEGATIVE_WORDS"


def test_inflected_forms_in_negative():
    for word in ("devastates", "crashed", "plummeted", "destroying", "damaged"):
        assert word in NEGATIVE_WORDS, f"'{word}' missing from NEGATIVE_WORDS"


def test_inflected_forms_in_positive():
    for word in ("increased", "soared", "grew", "boosted", "improving"):
        assert word in POSITIVE_WORDS, f"'{word}' missing from POSITIVE_WORDS"


def test_word_boundary_match_basic():
    assert has_word_boundary_match("stopped importing petrol", NEGATIVE_WORDS)
    assert not has_word_boundary_match("the waterfalls are beautiful", ["fall"])


def test_word_boundary_match_no_false_positive():
    # "fall" should NOT match inside "waterfalls"
    assert not has_word_boundary_match("waterfalls", ["fall"])
    # "cut" should NOT match inside "shortcut"
    assert not has_word_boundary_match("shortcut", ["cut"])
    # "rise" should NOT match inside "surprise"
    assert not has_word_boundary_match("surprise", ["rise"])


def test_word_boundary_match_positive():
    assert has_word_boundary_match("the economy will rise", POSITIVE_WORDS)
    assert has_word_boundary_match("investment is growing", POSITIVE_WORDS)

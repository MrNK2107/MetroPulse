def test_exact(resolver):
    r = resolver.resolve("Gaya")
    assert [m.name for m in r.matches][:1] == ["Gaya"] and r.ambiguous is False


def test_alias_old_name(resolver):
    r = resolver.resolve("Bombay", level="district")
    assert r.matches[0].name == "Mumbai" and r.matches[0].method == "alias"


def test_ambiguous_name_returns_all_candidates(resolver):
    r = resolver.resolve("Aurangabad", level="district")
    assert r.ambiguous is True
    assert {m.state_code for m in r.matches} == {"10", "27"}


def test_state_hint_disambiguates(resolver):
    r = resolver.resolve("Aurangabad", level="district", state_code="10")
    assert r.ambiguous is False and r.matches[0].state_code == "10"


def test_fuzzy_typo(resolver):
    m = resolver.resolve("Patnaa").matches[0]
    assert m.name == "Patna" and m.method == "fuzzy" and m.score >= 90


def test_unknown_returns_empty(resolver):
    r = resolver.resolve("Atlantis")
    assert r.matches == [] and r.ambiguous is False


def test_single_digit_state_alias(resolver):
    for st in (None, "06", "6"):
        r = resolver.resolve("Gurgaon", level="district", state_code=st)
        assert r.ambiguous is False
        m = r.matches[0]
        assert (m.name, m.method, m.state_code) == ("Gurugram", "alias", "06")
        assert m.place_id == "district:76"


def test_state_code_hint_is_zero_padded(resolver):
    assert resolver.resolve("Gurugram", state_code="6").matches[0].place_id == "district:76"


def _singhbhum_resolver():
    import pandas as pd

    from twin.places.normalize import normalize_name
    from twin.places.resolver import PlaceResolver

    rows = [("district:1", "East Singhbhum"), ("district:2", "West Singhbhum"),
            ("district:3", "Ranchi")]
    places = pd.DataFrame({
        "place_id": [p for p, _ in rows], "name": [n for _, n in rows],
        "name_norm": [normalize_name(n) for _, n in rows],
        "level": "district", "state_code": "20",
    })
    aliases = pd.DataFrame({"alias": [], "canonical": [], "state_code": []})
    return PlaceResolver(places, aliases)


def test_same_state_tie_is_ambiguous_not_a_silent_pick():
    r = _singhbhum_resolver().resolve("Singhbhum", level="district", state_code="20")
    assert r.ambiguous is True
    assert {m.name for m in r.matches} == {"East Singhbhum", "West Singhbhum"}
    assert _singhbhum_resolver().resolve("Singhbhum", level="district").ambiguous is True


def test_clear_fuzzy_winner_is_not_ambiguous():
    r = _singhbhum_resolver().resolve("Ranchii", level="district", state_code="20")
    assert r.ambiguous is False and r.matches[0].name == "Ranchi"

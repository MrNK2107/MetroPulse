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

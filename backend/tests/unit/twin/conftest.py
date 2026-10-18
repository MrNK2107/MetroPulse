from pathlib import Path

import pytest


@pytest.fixture
def fx() -> Path:
    return Path(__file__).parents[2] / "fixtures" / "twin"


@pytest.fixture
def places(fx):
    from twin.places.lgd import load_lgd

    return load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")


@pytest.fixture
def resolver(places, fx):
    from twin.places.resolver import PlaceResolver, load_aliases

    return PlaceResolver(places, load_aliases(fx / "aliases.csv"))

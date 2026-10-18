from pathlib import Path

import pytest


@pytest.fixture
def fx() -> Path:
    return Path(__file__).parents[2] / "fixtures" / "twin"

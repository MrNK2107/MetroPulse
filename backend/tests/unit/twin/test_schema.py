import pandas as pd
from twin.store.schema import OBSERVATION_COLUMNS, place_id, parse_place_id, validate_observations


def _row(**kw):
    base = dict(indicator="population_total", place_id="district:188", period="2011", value=1.0,
                unit="persons", source_id="census2011-pca", dataset_version="v1", trust_label="fact")
    base.update(kw); return base


def test_place_id_round_trip():
    assert place_id("district", "188") == "district:188"
    assert parse_place_id("h3r7:872830828ffffff") == ("h3r7", "872830828ffffff")


def test_valid_frame_has_no_problems():
    assert validate_observations(pd.DataFrame([_row()])) == []


def test_null_value_is_allowed():
    assert validate_observations(pd.DataFrame([_row(value=None)])) == []


def test_bad_trust_label_and_missing_column_reported():
    df = pd.DataFrame([_row(trust_label="guess")]).drop(columns=["unit"])
    problems = validate_observations(df)
    assert any("unit" in p for p in problems)
    assert any("trust_label" in p for p in problems)


def test_duplicate_key_reported():
    df = pd.DataFrame([_row(), _row()])
    assert any("duplicate" in p for p in validate_observations(df))

import pandas as pd
import pytest

from twin.places.lgd import load_lgd


def test_lgd_builds_hierarchy(fx):
    df = load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")
    gaya = df[(df.level == "district") & (df.name_norm == "gaya")].iloc[0]
    assert gaya.parent_id == "state:10"
    assert df[df.level == "state"].parent_id.eq("country:IN").all()
    assert (df.level == "country").sum() == 1


def test_new_district_has_null_census_code(fx):
    df = load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")
    assert df[df.level == "district"].census2011_code.isna().sum() == 1


def test_duplicate_lgd_code_raises(fx, tmp_path):
    bad = tmp_path / "d.csv"
    bad.write_text(
        "State Code,District Code,District Name (In English),Census 2011 Code\n"
        "10,1,A,\n10,1,B,\n"
    )
    with pytest.raises(ValueError):
        load_lgd(fx / "lgd_states.csv", bad, "v")

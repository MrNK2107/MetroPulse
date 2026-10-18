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
    assert df[df.level == "district"].census2011_code.isna().sum() == 2  # Newpur, Gurugram


def test_duplicate_lgd_code_raises(fx, tmp_path):
    bad = tmp_path / "d.csv"
    bad.write_text(
        "State Code,District Code,District Name (In English),Census 2011 Code\n"
        "10,1,A,\n10,1,B,\n"
    )
    with pytest.raises(ValueError):
        load_lgd(fx / "lgd_states.csv", bad, "v")


def test_single_digit_state_code_is_zero_padded(fx):
    df = load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")
    st = df[(df.level == "state") & (df.name == "Haryana")].iloc[0]
    assert (st.place_id, st.lgd_code, st.state_code) == ("state:06", "06", "06")
    gu = df[(df.level == "district") & (df.name == "Gurugram")].iloc[0]
    assert (gu.parent_id, gu.state_code) == ("state:06", "06")


def test_missing_headers_raise_with_expected_and_found(fx, tmp_path):
    bad = tmp_path / "d.csv"
    bad.write_text("StateCode,District Code,District Name (In English),Census 2011 Code\n10,1,A,\n")
    with pytest.raises(ValueError) as e:
        load_lgd(fx / "lgd_states.csv", bad, "v")
    msg = str(e.value)
    assert "State Code" in msg and "expected" in msg and "found" in msg and "StateCode" in msg

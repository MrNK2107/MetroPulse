import warnings

import pytest

from twin.pipeline.base import run_pipeline
from twin.pipeline.census2011 import Census2011Adapter
from twin.store.parquet_store import query_observations

from .conftest import NEW_DISTRICT_ID, X_ID, Y_ID, Z_ID

INDIA_TOTAL = 6_600_000


def _parse(ctx):
    a = Census2011Adapter()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        return a.parse(a.input_files(ctx.paths.manual), ctx)


def _pop(obs, pid):
    r = obs[(obs.place_id == pid) & (obs.indicator == "population_total")]
    return r.iloc[0] if len(r) else None


def test_national_population_conserved(ctx_census):
    obs = _parse(ctx_census)
    tot = obs[obs.indicator == "population_total"].value.sum()
    assert tot == pytest.approx(INDIA_TOTAL, rel=1e-4)


def test_split_district_marked_pattern(ctx_census):
    obs = _parse(ctx_census)
    y, z = _pop(obs, Y_ID), _pop(obs, Z_ID)
    assert y.trust_label == "pattern" and z.trust_label == "pattern"
    assert y.value == pytest.approx(600_000, rel=1e-3)
    assert z.value == pytest.approx(400_000, rel=1e-3)


def test_one_to_one_is_fact_and_helper_columns_dropped(ctx_census):
    obs = _parse(ctx_census)
    assert _pop(obs, X_ID).trust_label == "fact"
    assert _pop(obs, X_ID).value == pytest.approx(2_000_000)
    assert "n_sources" not in obs.columns and "max_weight" not in obs.columns
    assert set(obs.indicator) == {
        "population_total", "population_male", "population_female",
        "literates_total", "workers_total",
    }
    assert set(obs.source_id) == {"census2011-pca-district"} and set(obs.period) == {"2011"}


def test_new_district_without_2011_link_has_no_population(ctx_census):
    obs = _parse(ctx_census)
    assert _pop(obs, NEW_DISTRICT_ID) is None
    a = Census2011Adapter()
    rep = a.validate(obs, ctx_census)
    assert rep.ok, rep.problems
    assert NEW_DISTRICT_ID in rep.stats["districts_without_value"]


def test_publishes_through_pipeline_with_real_version(ctx_census):
    r = run_pipeline(Census2011Adapter(), ctx_census)
    assert r.published
    df = query_observations(ctx_census.paths, indicators=["population_total"])
    assert set(df.dataset_version) == {r.dataset_version}


def test_tampered_india_total_fails_validation(ctx_census):
    f = ctx_census.paths.manual / "census2011" / "pca_district.csv"
    f.write_text(f.read_text().replace("INDIA,6600000", "INDIA,6700000"))
    r = run_pipeline(Census2011Adapter(), ctx_census)
    assert r.published is False
    assert any("INDIA" in p or "India" in p for p in r.report.problems)


def test_numeric_codes_are_zero_padded(ctx_census):
    f = ctx_census.paths.manual / "census2011" / "pca_district.csv"
    f.write_text(f.read_text().replace("\n10,226,", "\n10.0,226.0,").replace("\n31,587,", "\n31,587,"))
    obs = _parse(ctx_census)
    assert _pop(obs, X_ID).value == pytest.approx(2_000_000)


def test_unmapped_old_district_is_a_problem(ctx_census):
    f = ctx_census.paths.manual / "census2011" / "pca_district.csv"
    f.write_text(f.read_text() + "27,999,DISTRICT,Total,Ghost,100,50,50,80,30\n")
    a = Census2011Adapter()
    with pytest.warns(UserWarning):
        obs = a.parse(a.input_files(ctx_census.paths.manual), ctx_census)
    rep = a.validate(obs, ctx_census)
    assert not rep.ok
    assert any("census2011_district:27999" in p for p in rep.problems)

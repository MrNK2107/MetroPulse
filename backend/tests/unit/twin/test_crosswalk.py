import numpy as np
import pandas as pd
import pytest

from tests.unit.twin.conftest import (
    NEW_DISTRICT_ID, OLD_A_ID, OLD_B_ID, OLD_C_ID, X_ID, Y_ID, Z_ID,
)
from twin.places.crosswalk import apply_crosswalk, build_crosswalk
from twin.store.schema import OBSERVATION_COLUMNS


def obs_frame(values: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "indicator": "population_total", "place_id": pid, "period": "2011",
                "value": v, "unit": "persons", "source_id": "test",
                "dataset_version": "v", "trust_label": "fact",
            }
            for pid, v in values.items()
        ],
        columns=list(OBSERVATION_COLUMNS),
    )


def test_weights_sum_to_one_and_drop_slivers(old, new):
    x = build_crosswalk(old, new)
    assert x.groupby("old_id").area_weight.sum().round(9).eq(1).all()
    assert not ((x.old_id == OLD_C_ID) & (x.area_weight < 0.005)).any()
    assert x.pop_weight.isna().all()
    assert NEW_DISTRICT_ID not in set(x.new_id)


def test_split_district_conserves_total(old, new):
    x = build_crosswalk(old, new)
    obs = obs_frame({OLD_A_ID: 100, OLD_B_ID: 1000, OLD_C_ID: 10})
    out = apply_crosswalk(obs, x, "sum")
    assert out.value.sum() == pytest.approx(1110)
    s = out.set_index("place_id")
    assert s.value[Y_ID] == pytest.approx(600, rel=1e-3)
    assert s.value[Z_ID] == pytest.approx(400, rel=1e-3)
    assert s.n_sources[Y_ID] == 1
    assert s.max_weight[Y_ID] == pytest.approx(0.6, rel=1e-3)
    assert out.trust_label.eq("fact").all()


def test_null_stays_null(old, new):
    out = apply_crosswalk(obs_frame({OLD_A_ID: None}), build_crosswalk(old, new), "sum")
    assert out.set_index("place_id").value.isna()[X_ID]


def test_sum_partial_null_sums_non_null():
    x = pd.DataFrame({"old_id": ["a", "b"], "new_id": ["n", "n"],
                      "area_weight": [0.5, 1.0], "pop_weight": [np.nan] * 2})
    out = apply_crosswalk(obs_frame({"a": None, "b": 10}), x, "sum")
    assert out.value.iloc[0] == pytest.approx(10)
    assert out.n_sources.iloc[0] == 2


def test_mean_is_weighted_and_skips_nulls():
    x = pd.DataFrame({"old_id": ["a", "b", "c"], "new_id": ["n"] * 3,
                      "area_weight": [0.25, 0.75, 1.0], "pop_weight": [np.nan] * 3})
    out = apply_crosswalk(obs_frame({"a": 10, "b": 20, "c": None}), x, "mean")
    assert out.value.iloc[0] == pytest.approx(17.5)
    out = apply_crosswalk(obs_frame({"a": None, "b": None, "c": None}), x, "mean")
    assert out.value.isna().all()


def test_pop_weights_used_when_provided(old, new):
    pw = pd.DataFrame({"old_id": [OLD_B_ID, OLD_B_ID], "new_id": [Y_ID, Z_ID],
                       "population": [900.0, 100.0]})
    x = build_crosswalk(old, new, pop_weights=pw)
    b = x[x.old_id == OLD_B_ID].set_index("new_id")
    assert b.pop_weight[Y_ID] == pytest.approx(0.9)
    out = apply_crosswalk(obs_frame({OLD_B_ID: 1000}), x, "sum", weight="pop")
    assert out.set_index("place_id").value[Y_ID] == pytest.approx(900)

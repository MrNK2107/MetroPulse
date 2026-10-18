from twin.pipeline.base import Indicator
from twin.store.catalog import list_indicators, search_indicators, upsert_indicators


def _pop():
    return Indicator("population_total", "Total population", "All persons", "persons",
                     ("population",), "census2011-pca-district")


def test_catalog_search(tmp_paths):
    upsert_indicators(tmp_paths, [_pop()])
    assert search_indicators(tmp_paths, "population")[0].id == "population_total"
    assert search_indicators(tmp_paths, "zzzz unrelated") == []


def test_upsert_replaces_by_id_and_empty_catalog(tmp_paths):
    assert list_indicators(tmp_paths) == []
    assert search_indicators(tmp_paths, "population") == []
    upsert_indicators(tmp_paths, [_pop()])
    p = _pop()
    p.name = "Population (renamed)"
    upsert_indicators(tmp_paths, [p])
    got = list_indicators(tmp_paths)
    assert len(got) == 1 and got[0].name == "Population (renamed)"
    assert got[0].domains == ("population",)

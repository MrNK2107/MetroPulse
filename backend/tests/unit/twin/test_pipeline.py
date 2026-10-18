import pandas as pd
import pytest

from twin.pipeline.base import Indicator, ValidationReport, run_pipeline
from twin.store.parquet_store import (
    is_published, query_observations, read_current,
)

from .conftest import X_ID, Y_ID


class DummyAdapter:
    indicators = [Indicator("dummy_ind", "Dummy", "Dummy indicator", "n", ("population",), "dummy")]
    transform_version = "t1"

    def __init__(self, source_id="dummy", fail=False):
        self.source_id = source_id
        self.fail = fail

    def input_files(self, manual_dir):
        return sorted((manual_dir / "dummy").glob("*.csv"))

    def observed_period(self, files):
        return "2011"

    def parse(self, files, ctx):
        return pd.DataFrame({
            "indicator": ["dummy_ind"] * 2, "place_id": [X_ID, Y_ID], "period": ["2011"] * 2,
            "value": [1.0, 2.0], "unit": ["n"] * 2, "source_id": [self.source_id] * 2,
            "dataset_version": ["x"] * 2, "trust_label": ["fact"] * 2,
        })

    def validate(self, obs, ctx):
        return ValidationReport(ok=not self.fail, problems=["forced"] if self.fail else [], stats={})


def ctx_file_append(ctx, text):
    f = ctx.paths.manual / "dummy" / "d.csv"
    f.write_text(f.read_text() + text)


@pytest.fixture(autouse=True)
def _csv(ctx):
    d = ctx.paths.manual / "dummy"
    d.mkdir(parents=True)
    (d / "d.csv").write_text("a,b\n1,2\n")


def test_unknown_source_rejected(ctx):
    with pytest.raises(KeyError):
        run_pipeline(DummyAdapter(source_id="nope"), ctx)


def test_publish_writes_raw_manifest_and_current(ctx):
    r = run_pipeline(DummyAdapter(), ctx)
    assert r.published and not r.reused
    assert any((ctx.paths.raw / "dummy").glob("*/manifest.json"))
    assert read_current(ctx.paths)["dummy"] == r.dataset_version
    assert "@2011#" in r.dataset_version


def test_failed_validation_does_not_publish(ctx):
    r = run_pipeline(DummyAdapter(fail=True), ctx)
    assert r.published is False and "dummy" not in read_current(ctx.paths)
    assert not (ctx.paths.published / "datasets").exists()


def test_rerun_same_input_is_idempotent(ctx):
    a = run_pipeline(DummyAdapter(), ctx)
    b = run_pipeline(DummyAdapter(), ctx)
    assert b.reused and a.dataset_version == b.dataset_version


def test_changed_input_creates_new_version(ctx):
    a = run_pipeline(DummyAdapter(), ctx)
    ctx_file_append(ctx, "x")
    b = run_pipeline(DummyAdapter(), ctx)
    assert a.dataset_version != b.dataset_version
    assert is_published(ctx.paths, "dummy", a.dataset_version)
    assert read_current(ctx.paths)["dummy"] == b.dataset_version


def test_query_observations_filters_and_source_names(ctx):
    r = run_pipeline(DummyAdapter(), ctx)
    df = query_observations(ctx.paths, place_ids=[X_ID], indicators=["dummy_ind"],
                            source_names={"dummy": "Dummy Source"})
    assert list(df["place_id"]) == [X_ID]
    assert df["source_name"].iloc[0] == "Dummy Source"
    assert df["dataset_version"].iloc[0] == r.dataset_version
    assert query_observations(ctx.paths, indicators=["nope"]).empty
    assert query_observations(ctx.paths)["source_name"].iloc[0] == "dummy"


def test_query_empty_store(tmp_paths):
    df = query_observations(tmp_paths)
    assert df.empty and "source_name" in df.columns and "place_id" in df.columns


def test_failed_write_leaves_nothing_then_clean_run_publishes(ctx, monkeypatch):
    real = pd.DataFrame.to_parquet

    def boom(self, *a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", boom)
    with pytest.raises(RuntimeError):
        run_pipeline(DummyAdapter(), ctx)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", real)
    src = ctx.paths.published / "datasets" / "dummy"
    assert not list(src.iterdir())  # no final dir, no tmp leftovers
    assert "dummy" not in read_current(ctx.paths)
    r = run_pipeline(DummyAdapter(), ctx)
    assert r.published and not r.reused
    assert is_published(ctx.paths, "dummy", r.dataset_version)


def test_reuse_heals_catalogue_and_current(ctx):
    from twin.store.catalog import list_indicators
    from twin.store.parquet_store import set_current

    a = run_pipeline(DummyAdapter(), ctx)
    (ctx.paths.published / "catalog" / "indicators.parquet").unlink()
    ctx.paths.current_file.unlink()
    b = run_pipeline(DummyAdapter(), ctx)
    assert b.reused and read_current(ctx.paths)["dummy"] == a.dataset_version
    assert [i.id for i in list_indicators(ctx.paths)] == ["dummy_ind"]


def _fake_places(ctx, version, digest):
    d = ctx.paths.places_dir(version)
    d.mkdir(parents=True, exist_ok=True)
    (d / "places_digest.txt").write_text(digest)
    ctx.places_version = version


def test_version_covers_transform_places_and_filename(ctx):
    base = run_pipeline(DummyAdapter(), ctx).dataset_version
    t = DummyAdapter()
    t.transform_version = "t2"
    v_t = run_pipeline(t, ctx).dataset_version
    _fake_places(ctx, "lgd-x", "digest-1")
    v_p = run_pipeline(DummyAdapter(), ctx).dataset_version
    d = ctx.paths.manual / "dummy"
    (d / "d.csv").rename(d / "e.csv")
    v_n = run_pipeline(DummyAdapter(), ctx).dataset_version
    assert len({base, v_t, v_p, v_n}) == 4


def test_version_follows_places_digest_not_version_name(ctx):
    _fake_places(ctx, "lgd-x", "digest-1")
    a = run_pipeline(DummyAdapter(), ctx).dataset_version
    _fake_places(ctx, "lgd-x", "digest-2")  # same version name, rebuilt content
    b = run_pipeline(DummyAdapter(), ctx).dataset_version
    _fake_places(ctx, "lgd-y", "digest-2")  # new name, same content
    c = run_pipeline(DummyAdapter(), ctx).dataset_version
    assert a != b and b == c


def test_missing_places_digest_is_an_error(ctx):
    ctx.places_version = "lgd-missing"
    with pytest.raises(FileNotFoundError, match="places_digest"):
        run_pipeline(DummyAdapter(), ctx)


def test_chunked_hash_matches_whole_file_hash(tmp_path, monkeypatch):
    import hashlib

    from twin.pipeline import base

    f = tmp_path / "a.bin"
    f.write_bytes(bytes(range(256)) * 41)
    monkeypatch.setattr(base, "HASH_CHUNK_BYTES", 7)
    combined, per_file = base._hash_inputs([f], "tv", "pd")
    assert per_file["a.bin"] == hashlib.sha256(f.read_bytes()).hexdigest()
    ref = hashlib.sha256(b"a.bin\x00" + f.read_bytes() + b"\x00tv" + b"\x00pd").hexdigest()
    assert combined == ref == base._sha256([f], "tv", "pd")


def _manifest(ctx):
    import json

    (m,) = list((ctx.paths.raw / "dummy").glob("*/manifest.json"))
    return m.parent, json.loads(m.read_text())


def test_manifest_records_each_file_and_places(ctx):
    import hashlib
    import json

    r = run_pipeline(DummyAdapter(), ctx)
    raw, man = _manifest(ctx)
    (entry,) = man["files"]
    src = ctx.paths.manual / "dummy" / "d.csv"
    assert entry["name"] == "d.csv" and entry["size"] == src.stat().st_size
    assert entry["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert entry["copied"] is True and (raw / "d.csv").exists()
    assert man["places_version"] is None and man["places_digest"] == ""
    rep = json.loads((ctx.paths.dataset_dir("dummy", r.dataset_version) / "report.json").read_text())
    assert rep["places_version"] is None and rep["places_digest"] == ""


def test_large_input_is_hardlinked_not_copied(ctx, monkeypatch):
    from twin.pipeline import base

    monkeypatch.setattr(base, "RAW_COPY_MAX_BYTES", 2)
    run_pipeline(DummyAdapter(), ctx)
    raw, man = _manifest(ctx)
    (entry,) = man["files"]
    assert entry["copied"] is False and entry["hardlinked"] is True
    assert (raw / "d.csv").stat().st_nlink >= 2


def test_large_input_referenced_when_hardlink_fails(ctx, monkeypatch):
    from twin.pipeline import base

    def no_link(*a, **k):
        raise OSError("cross-device link")

    monkeypatch.setattr(base, "RAW_COPY_MAX_BYTES", 2)
    monkeypatch.setattr(base.os, "link", no_link)
    run_pipeline(DummyAdapter(), ctx)
    raw, man = _manifest(ctx)
    (entry,) = man["files"]
    assert entry["copied"] is False and entry["hardlinked"] is False
    assert not (raw / "d.csv").exists()
    assert entry["source_path"] == str((ctx.paths.manual / "dummy" / "d.csv").resolve())


def test_set_current_on_publish_false_leaves_current(ctx):
    a = run_pipeline(DummyAdapter(), ctx, set_current_on_publish=False)
    assert a.published and "dummy" not in read_current(ctx.paths)
    b = run_pipeline(DummyAdapter(), ctx, set_current_on_publish=False)
    assert b.reused and "dummy" not in read_current(ctx.paths)

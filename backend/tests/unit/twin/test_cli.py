import json
from pathlib import Path

from scripts.twin_build import EXPECTED_MANUAL_FILES, main, render_manual_readme

REPO = Path(__file__).resolve().parents[4]


def test_check_reports_missing_files(tmp_paths, capsys):
    assert main(["check"], paths=tmp_paths) == 1
    out = capsys.readouterr().out
    assert "lgd/districts.csv" in out and "✗" in out


def test_check_passes_on_fixtures(fixture_manual_paths, capsys):
    assert main(["check"], paths=fixture_manual_paths) == 0
    assert "✗" not in capsys.readouterr().out


def test_build_runs_on_fixtures(fixture_manual_paths, capsys):
    assert main(["build", "--boundary-version", "lgd-test"], paths=fixture_manual_paths) == 0
    out = capsys.readouterr().out
    lines = [json.loads(x) for x in out.splitlines() if x.strip()]  # stdout is pure JSON lines
    assert len(lines) == 3  # report + census + viirs
    assert lines[0]["unmatched_boundaries"] == []
    assert all(r["report"]["ok"] for r in lines[1:])


def test_check_survives_cp1252_stdout(tmp_paths, monkeypatch):
    import io
    import sys

    buf = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buf, encoding="cp1252"))
    assert main(["check"], paths=tmp_paths) == 1
    sys.stdout.flush()
    assert "lgd/districts.csv" in buf.getvalue().decode("utf-8")


def test_build_fails_on_unmatched_boundary(fixture_manual_paths, capsys):
    f = fixture_manual_paths.manual / "soi" / "district_boundaries.geojson"
    f.write_text(f.read_text(encoding="utf-8").replace("PATNA", "ZZZ NOWHERE"), encoding="utf-8")
    assert main(["build", "--boundary-version", "lgd-test"], paths=fixture_manual_paths) == 1
    assert "unmatched boundaries" in capsys.readouterr().err


def test_build_fails_when_file_missing(tmp_paths, capsys):
    assert main(["build", "--boundary-version", "lgd-test"], paths=tmp_paths) == 1
    cap = capsys.readouterr()
    assert "missing manual files" in cap.err and cap.out == ""


def test_sync_without_dsn_skips(tmp_paths, capsys, monkeypatch):
    monkeypatch.delenv("TWIN_PG_DSN", raising=False)
    assert main(["sync"], paths=tmp_paths) == 0
    assert "postgres sync skipped" in capsys.readouterr().err


def test_committed_readme_matches_generator():
    assert (REPO / "data/twin/manual/README.md").read_text(encoding="utf-8") == render_manual_readme()
    assert all(rel in render_manual_readme() for rel in EXPECTED_MANUAL_FILES)


def test_successful_build_sets_all_current_keys_together(fixture_manual_paths, capsys):
    from twin.store.parquet_store import read_current

    assert main(["build", "--boundary-version", "lgd-test"], paths=fixture_manual_paths) == 0
    out = [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.strip()]
    cur = read_current(fixture_manual_paths)
    assert cur == {
        "places": "lgd-test",
        "census2011-pca-district": out[1]["dataset_version"],
        "viirs": out[2]["dataset_version"],
    }


def test_build_failing_a_gate_leaves_current_unchanged(fixture_manual_paths, capsys):
    from twin.store.parquet_store import read_current

    assert main(["build", "--boundary-version", "lgd-a"], paths=fixture_manual_paths) == 0
    before = read_current(fixture_manual_paths)
    f = fixture_manual_paths.manual / "soi" / "district_boundaries.geojson"
    f.write_text(f.read_text(encoding="utf-8").replace("PATNA", "ZZZ NOWHERE"), encoding="utf-8")
    assert main(["build", "--boundary-version", "lgd-b"], paths=fixture_manual_paths) == 1
    assert read_current(fixture_manual_paths) == before


def test_failing_census_validation_leaves_current_unchanged(fixture_manual_paths, capsys):
    from twin.store.parquet_store import read_current

    f = fixture_manual_paths.manual / "census2011" / "pca_district.csv"
    f.write_text(f.read_text().replace("INDIA,6600000", "INDIA,6700000"))
    assert main(["build", "--boundary-version", "lgd-test"], paths=fixture_manual_paths) == 1
    assert "census2011-pca-district validation" in capsys.readouterr().err
    assert read_current(fixture_manual_paths) == {}


def test_default_paths_follow_settings(monkeypatch, tmp_path):
    from app.config import settings
    from scripts.twin_build import default_paths
    from twin.paths import TwinPaths

    monkeypatch.setattr(settings, "twin_data_dir", str(tmp_path / "custom"))
    assert default_paths() == TwinPaths(tmp_path / "custom")
    monkeypatch.setattr(settings, "twin_data_dir", "")
    monkeypatch.delenv("TWIN_DATA_DIR", raising=False)
    assert default_paths() == TwinPaths.default()

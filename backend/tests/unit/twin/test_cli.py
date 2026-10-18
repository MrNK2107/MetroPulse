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

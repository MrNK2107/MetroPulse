"""Checks the stats helpers in scripts/bench_api.py against hand-computed values and numpy."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "bench_api.py"
_spec = importlib.util.spec_from_file_location("bench_api", _SCRIPT)
bench = importlib.util.module_from_spec(_spec)
sys.modules["bench_api"] = bench  # dataclasses look the module up while executing it
_spec.loader.exec_module(bench)


def test_percentile_hand_computed():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert bench.percentile(xs, 0) == 1.0
    assert bench.percentile(xs, 50) == 3.0
    assert bench.percentile(xs, 100) == 5.0
    # rank = 0.95 * 4 = 3.8 -> 4 + 0.8 * (5 - 4)
    assert bench.percentile(xs, 95) == pytest.approx(4.8)
    # order of input must not matter
    assert bench.percentile([5.0, 1.0, 4.0, 2.0, 3.0], 95) == pytest.approx(4.8)


@pytest.mark.parametrize("p", [1, 25, 50, 90, 95, 99, 99.9])
def test_percentile_matches_numpy(p):
    rng = np.random.default_rng(42)
    xs = rng.lognormal(mean=1.0, sigma=0.6, size=997).tolist()
    assert bench.percentile(xs, p) == pytest.approx(float(np.percentile(xs, p)))


def test_percentile_single_and_errors():
    assert bench.percentile([7.5], 99) == 7.5
    with pytest.raises(ValueError):
        bench.percentile([], 50)
    with pytest.raises(ValueError):
        bench.percentile([1.0], 101)


def test_summarize():
    lat = [float(i) for i in range(1, 101)]  # 1..100 ms
    s = bench.summarize(lat, wall_seconds=2.0)
    assert s["n"] == 100
    assert s["min"] == 1.0 and s["max"] == 100.0
    assert s["mean"] == pytest.approx(50.5)
    assert s["p50"] == pytest.approx(50.5)
    assert s["p95"] == pytest.approx(95.05)
    assert s["p99"] == pytest.approx(99.01)
    assert s["rps"] == pytest.approx(50.0)
    with pytest.raises(ValueError):
        bench.summarize([], 1.0)
    with pytest.raises(ValueError):
        bench.summarize([1.0], 0.0)

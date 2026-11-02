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


# ── 429 handling ────────────────────────────────────────────────────────


def test_drive_propagates_rate_limited():
    import asyncio

    async def op():
        raise bench.RateLimited("GET /x", "7")

    with pytest.raises(bench.RateLimited):
        asyncio.run(bench._drive(op, 3, 1))


def test_bench_http_aborts_on_429(monkeypatch):
    import asyncio

    import httpx

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(lambda req: httpx.Response(429, headers={"Retry-After": "12"}))
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)
    with pytest.raises(bench.RateLimited) as exc:
        asyncio.run(bench.bench_http("http://127.0.0.1:9", "/api/health", n=5, warmup=2, concurrency=1))
    assert exc.value.retry_after == "12"


def test_main_prints_clear_message_on_429(monkeypatch, capsys, tmp_path):
    async def fake_amain(args):
        raise bench.RateLimited("GET /api/regions", "30")

    monkeypatch.setattr(bench, "amain", fake_amain)
    monkeypatch.setattr(bench, "machine_info", lambda: {})
    out = tmp_path / "bench.md"
    assert bench.main(["--out", str(out)]) == 2
    err = capsys.readouterr().err
    assert "429" in err and "RATE_LIMIT_PER_MINUTE=0" in err
    assert not out.exists(), "no report should be written from a rate-limited run"

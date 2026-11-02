"""Benchmark a *running* MetroPulse backend.

This script starts nothing. Point it at a backend you started yourself, e.g.:

    cd backend
    $env:RATE_LIMIT_PER_MINUTE = "0"   # PowerShell; bash: export RATE_LIMIT_PER_MINUTE=0
    .venv\\Scripts\\uvicorn app.main:app --port 8020 --no-access-log --log-level warning
    .venv\\Scripts\\python ..\\scripts\\bench_api.py --base-url http://127.0.0.1:8020

It measures client-observed latency (p50/p95/p99) and throughput for the REST
endpoints that work without built twin data or LLM keys, at concurrency 1 and
8, after a warm-up. If AGENT_WS_TOKEN is set (env or --ws-token) it also times
the /ws/agent handshake (connect + accept) and a PING/PONG round trip.

Results are written as Markdown (default docs/benchmarks.md) together with
machine info and a load snapshot, because numbers from a busy shared machine
are only an upper bound on latency.

Start the server with RATE_LIMIT_PER_MINUTE=0 (as above). The default per-IP
limit (240 requests/minute) is far below what a benchmark sends from one
client, so a run against it would mostly time 429 responses. If any request
gets a 429 the script stops with exit status 2 and writes no report.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Sequence

# Endpoints that answer without twin data, an LLM key or Supabase.
DEFAULT_ENDPOINTS: list[str] = [
    "/api/health",
    "/api/agent/status",
    "/api/regions",
    "/api/regions/bengaluru/baseline",
    "/api/case-studies",
    "/api/case-studies?city=bengaluru&sector=transport",
    "/api/data-sources?city=bengaluru",
]


# --------------------------------------------------------------------------- stats

def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile (same as numpy's default 'linear' method).

    ``p`` is in [0, 100]. Raises ValueError on an empty input.
    """
    if not values:
        raise ValueError("percentile of empty sequence")
    if not 0.0 <= p <= 100.0:
        raise ValueError("p must be in [0, 100]")
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    rank = (p / 100.0) * (len(xs) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return float(xs[lo])
    frac = rank - lo
    return float(xs[lo] + (xs[hi] - xs[lo]) * frac)


def summarize(latencies_ms: Sequence[float], wall_seconds: float) -> dict[str, float]:
    """Summary stats for one run. Throughput = completed requests / wall time."""
    if not latencies_ms:
        raise ValueError("no samples")
    if wall_seconds <= 0:
        raise ValueError("wall_seconds must be positive")
    n = len(latencies_ms)
    return {
        "n": n,
        "min": float(min(latencies_ms)),
        "mean": float(sum(latencies_ms) / n),
        "p50": percentile(latencies_ms, 50),
        "p95": percentile(latencies_ms, 95),
        "p99": percentile(latencies_ms, 99),
        "max": float(max(latencies_ms)),
        "rps": n / wall_seconds,
    }


# --------------------------------------------------------------------------- runner

class RateLimited(Exception):
    """The server answered 429: the run would measure the rate limiter, not the API."""

    def __init__(self, target: str, retry_after: str | None = None):
        self.target = target
        self.retry_after = retry_after
        super().__init__(f"{target} returned 429 Too Many Requests")


@dataclass
class RunResult:
    target: str
    concurrency: int
    stats: dict[str, float]
    errors: int
    statuses: dict[str, int] = field(default_factory=dict)


async def _drive(
    op: Callable[[], Awaitable[str]], n: int, concurrency: int
) -> tuple[list[float], float, dict[str, int], int]:
    """Run ``op`` n times across ``concurrency`` workers. op returns a status label."""
    latencies: list[float] = []
    statuses: dict[str, int] = {}
    errors = 0
    remaining = n

    async def worker() -> None:
        nonlocal remaining, errors
        while remaining > 0:
            remaining -= 1
            t0 = time.perf_counter()
            try:
                label = await op()
            except RateLimited:
                raise
            except Exception as exc:  # network error, refused socket, ...
                label = type(exc).__name__
                errors += 1
            latencies.append((time.perf_counter() - t0) * 1000.0)
            statuses[label] = statuses.get(label, 0) + 1

    t0 = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    wall = time.perf_counter() - t0
    return latencies, wall, statuses, errors


async def bench_http(base_url: str, path: str, n: int, warmup: int, concurrency: int) -> RunResult:
    import httpx

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0, limits=limits) as client:

        async def op() -> str:
            r = await client.get(path)
            await r.aread()
            if r.status_code == 429:
                raise RateLimited(f"GET {path}", r.headers.get("Retry-After"))
            return str(r.status_code)

        await _drive(op, warmup, concurrency)
        lat, wall, statuses, errors = await _drive(op, n, concurrency)
    non2xx = sum(v for k, v in statuses.items() if not k.startswith("2"))
    return RunResult(f"GET {path}", concurrency, summarize(lat, wall), max(errors, non2xx), statuses)


async def bench_ws(base_url: str, token: str, n: int, warmup: int, concurrency: int) -> list[RunResult]:
    """Handshake (connect+accept) and PING/PONG round trip on /ws/agent."""
    import websockets

    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://").rstrip("/")
    ws_url = f"{ws_url}/ws/agent?token={token}"
    pong_lat: list[float] = []

    async def op() -> str:
        async with websockets.connect(ws_url, open_timeout=10, close_timeout=2) as ws:
            # the handshake time is measured by _drive; time one PING here too
            t0 = time.perf_counter()
            await ws.send(json.dumps({"type": "PING"}))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            pong_lat.append((time.perf_counter() - t0) * 1000.0)
            return "PONG" if msg.get("type") == "PONG" else str(msg.get("type"))

    # handshake-only op: open then close immediately
    async def handshake() -> str:
        async with websockets.connect(ws_url, open_timeout=10, close_timeout=2):
            return "open"

    await _drive(handshake, warmup, concurrency)
    lat, wall, statuses, errors = await _drive(handshake, n, concurrency)
    results = [RunResult("WS /ws/agent connect+accept+close", concurrency,
                         summarize(lat, wall), errors, statuses)]
    lat2, wall2, statuses2, errors2 = await _drive(op, n, concurrency)
    if pong_lat:
        # report the PING->PONG part only; throughput is full sessions/s
        st = summarize(pong_lat, wall2)
        st["rps"] = len(lat2) / wall2
        results.append(RunResult("WS /ws/agent PING->PONG (rps = full sessions/s)",
                                 concurrency, st, errors2, statuses2))
    return results


# --------------------------------------------------------------------------- report

def machine_info() -> dict[str, str]:
    info = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor() or platform.machine(),
        "logical_cpus": str(os.cpu_count()),
        "python (client)": sys.version.split()[0],
    }
    try:
        import psutil

        info["ram_total_gb"] = f"{psutil.virtual_memory().total / 2**30:.1f}"
        info["cpu_percent_at_start"] = f"{psutil.cpu_percent(interval=1.0):.0f}%"
        info["ram_used_at_start"] = f"{psutil.virtual_memory().percent:.0f}%"
        info["process_count"] = str(len(psutil.pids()))
    except Exception:
        pass
    return info


def render_markdown(results: list[RunResult], info: dict[str, str], args: argparse.Namespace,
                    load_after: str) -> str:
    lines = [
        "# MetroPulse API benchmarks",
        "",
        f"Generated by `scripts/bench_api.py` on {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        "Client-observed latency from a Python `httpx`/`websockets` client on the same machine as",
        "the server (loopback, keep-alive). One uvicorn worker. Times include client overhead.",
        f"Each row: {args.warmup} warm-up requests (discarded), then {args.requests} measured requests",
        f"({args.ws_requests} for WebSocket rows).",
        "",
    ]
    if args.server_note:
        lines += [f"Server: {args.server_note}", ""]
    lines += [
        "## Machine",
        "",
    ]
    lines += [f"- **{k}**: {v}" for k, v in info.items()]
    lines += [f"- **cpu_percent_at_end**: {load_after}", ""]
    lines += [
        "> **Load caveat.** This machine was shared with other jobs while measuring (see CPU %",
        "> above). Treat the latencies as an upper bound and the throughput as a lower bound.",
        "> Re-run on an idle machine before quoting tighter numbers.",
        "",
        "## Results",
        "",
        "| Target | Conc. | n | p50 ms | p95 ms | p99 ms | max ms | req/s | non-OK |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        s = r.stats
        lines.append(
            f"| `{r.target}` | {r.concurrency} | {int(s['n'])} | {s['p50']:.2f} | {s['p95']:.2f} "
            f"| {s['p99']:.2f} | {s['max']:.2f} | {s['rps']:.0f} | {r.errors} |"
        )
    lines += [
        "",
        "Status counts per row: " + "; ".join(
            f"`{r.target}` c={r.concurrency}: {r.statuses}" for r in results if r.errors
        ) if any(r.errors for r in results) else "All measured requests returned 2xx / PONG.",
        "",
        "## Not measured",
        "",
        "- `/api/twin/*` with real data: the twin has not been built on this machine, so those",
        "  routes return the 503 \"not built\" response; benchmarking that would be misleading.",
        "- Agent runs (`AGENT_START`): need an LLM key; latency would be dominated by the model.",
        "",
    ]
    return "\n".join(lines)


async def amain(args: argparse.Namespace) -> list[RunResult]:
    results: list[RunResult] = []
    for path in args.endpoints:
        for c in args.concurrency:
            r = await bench_http(args.base_url, path, args.requests, args.warmup, c)
            print(f"{r.target:55s} c={c} p50={r.stats['p50']:.2f} p95={r.stats['p95']:.2f} "
                  f"p99={r.stats['p99']:.2f} rps={r.stats['rps']:.0f} non-ok={r.errors}", flush=True)
            results.append(r)
    if args.ws_token:
        for c in args.concurrency:
            for r in await bench_ws(args.base_url, args.ws_token, args.ws_requests, args.warmup, c):
                print(f"{r.target:55s} c={c} p50={r.stats['p50']:.2f} p95={r.stats['p95']:.2f} "
                      f"p99={r.stats['p99']:.2f} rps={r.stats['rps']:.0f} non-ok={r.errors}", flush=True)
                results.append(r)
    else:
        print("AGENT_WS_TOKEN not set: skipping /ws/agent", flush=True)
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--requests", type=int, default=1000, help="measured requests per row")
    ap.add_argument("--ws-requests", type=int, default=200, help="measured WS sessions per row")
    ap.add_argument("--warmup", type=int, default=50)
    ap.add_argument("--concurrency", type=int, nargs="+", default=[1, 8])
    ap.add_argument("--endpoints", nargs="+", default=DEFAULT_ENDPOINTS)
    ap.add_argument("--ws-token", default=os.environ.get("AGENT_WS_TOKEN", ""))
    ap.add_argument("--server-note", default="", help="how the server was started (goes in the report)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "docs" / "benchmarks.md"))
    args = ap.parse_args(argv)

    info = machine_info()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        results = asyncio.run(amain(args))
    except RateLimited as exc:
        wait = f" (Retry-After: {exc.retry_after}s)" if exc.retry_after else ""
        print(
            f"error: {exc}{wait}. The server's per-IP rate limit is on, so the numbers\n"
            "would be meaningless. Restart the backend with RATE_LIMIT_PER_MINUTE=0 and\n"
            "run again. No report was written.",
            file=sys.stderr,
        )
        return 2
    load_after = info.get("cpu_percent_at_start", "n/a")
    try:
        import psutil

        load_after = f"{psutil.cpu_percent(interval=1.0):.0f}%"
    except Exception:
        pass
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_markdown(results, info, args, load_after), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

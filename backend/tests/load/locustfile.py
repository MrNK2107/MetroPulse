"""Locust load test for the token-gated agent socket, /ws/agent.

Each simulated user opens /ws/agent with AGENT_WS_TOKEN, sends PING, waits for
PONG and closes. That exercises the auth gate, the connection limiter
(WS_MAX_CONNECTIONS) and the socket path without calling an LLM; agent runs
(AGENT_START) are not load-tested because their latency is the model's.

Usage (backend started with the same AGENT_WS_TOKEN; keep the user count at or
below WS_MAX_CONNECTIONS, or expect 1013 closes reported as failures):

  export AGENT_WS_TOKEN=...            # PowerShell: $env:AGENT_WS_TOKEN = "..."
  locust -f tests/load/locustfile.py --host=http://localhost:8000

For REST latency use scripts/bench_api.py instead.
"""
from __future__ import annotations

import json
import os
import time
from urllib.parse import quote

from locust import User, between, task
from websockets.sync.client import connect


def agent_ws_url(host: str, token: str) -> str:
    base = host.rstrip("/").replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    return f"{base}/ws/agent?token={quote(token, safe='')}"


class AgentSocketUser(User):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        token = os.environ.get("AGENT_WS_TOKEN", "")
        if not token:
            raise RuntimeError("Set AGENT_WS_TOKEN to the backend's token before running locust.")
        self.url = agent_ws_url(self.host or "http://localhost:8000", token)

    def _fire(self, name: str, start: float, exc: Exception | None) -> None:
        self.environment.events.request.fire(
            request_type="WS",
            name=name,
            response_time=(time.perf_counter() - start) * 1000.0,
            response_length=0,
            exception=exc,
            context={},
        )

    @task
    def ping_pong(self) -> None:
        start = time.perf_counter()
        try:
            with connect(self.url, open_timeout=10, close_timeout=2) as ws:
                ws.send(json.dumps({"type": "PING"}))
                reply = json.loads(ws.recv(timeout=10))
                if reply.get("type") != "PONG":
                    raise RuntimeError(f"expected PONG, got {reply.get('type')!r}")
        except Exception as exc:  # refused, 1008/1013 close, timeout, wrong reply
            self._fire("/ws/agent PING->PONG", start, exc)
            return
        self._fire("/ws/agent PING->PONG", start, None)

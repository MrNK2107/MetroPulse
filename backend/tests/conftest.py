"""Suite-wide guard: tests must not touch the real network.

Every test runs with ``socket.getaddrinfo`` and ``socket.socket.connect``/``connect_ex``
patched so that only loopback hosts (``localhost``, 127.0.0.0/8, ``::1``) and
unix sockets are allowed. Any other lookup or connect raises ``NetworkBlocked``
(an ``OSError``, so code under test sees an ordinary network failure) and is
recorded; the test then fails at teardown even if the code under test swallowed
the error. This matters here because the realtime connectors catch every
exception and return ``None``.

Opt out for a deliberate live test with ``@pytest.mark.allow_network``.
"""
from __future__ import annotations

import asyncio
import asyncio.proactor_events
import asyncio.selector_events
import ipaddress
import os
import socket
import sys

import pytest

# Hermetic settings: environment variables beat backend/.env in pydantic-settings, so
# setting them here (before any app module is imported) stops the suite from using a
# developer's real Supabase project or LLM keys. Without this, tests that touch
# DatabaseClient read and wrote the live Supabase tables named in .env.
_HERMETIC_ENV = {
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "MIMO_API_KEY": "",
    "LLM_PROVIDER": "mimo",
    "LLM_MODEL": "",
    "EMBEDDING_PROVIDER": "",
    "EMBEDDING_MODEL": "",
    # Port 9 (discard) on loopback: refused at once, so a local Ollama never answers tests.
    "OLLAMA_BASE_URL": "http://127.0.0.1:9",
    # The suite fires hundreds of requests from one test client; the per-IP limiter has its own tests.
    "RATE_LIMIT_PER_MINUTE": "0",
    "OLLAMA_NUM_CTX": "8192",
    "INGEST_TOKEN": "",
}
os.environ.update(_HERMETIC_ENV)

_real_getaddrinfo = socket.getaddrinfo
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex

# asyncio connects through loop.sock_connect. On Windows the Proactor loop uses ConnectEx
# there and skips socket.connect, and an IP-literal host skips getaddrinfo too, so the
# event-loop classes are guarded as well.
_LOOP_CLASSES = [asyncio.selector_events.BaseSelectorEventLoop]
if sys.platform == "win32":
    _LOOP_CLASSES.append(asyncio.proactor_events.BaseProactorEventLoop)
_real_sock_connect = {cls: cls.sock_connect for cls in _LOOP_CLASSES}


class NetworkBlocked(OSError):
    """Raised when a test tries to reach a non-loopback host."""


def _is_local_host(host: object) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    if not isinstance(host, str):
        return False
    host = host.strip("[]").lower()
    if host in ("", "localhost", "localhost.localdomain"):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _is_local_address(address: object) -> bool:
    # AF_UNIX addresses are str/bytes paths; AF_INET/AF_INET6 are tuples.
    if isinstance(address, tuple) and address:
        return _is_local_host(address[0])
    return isinstance(address, (str, bytes))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "allow_network: let this test open real (non-loopback) network connections"
    )


@pytest.fixture(autouse=True)
def _block_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    if request.node.get_closest_marker("allow_network"):
        yield
        return

    attempts: list[str] = []

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_local_host(host):
            attempts.append(f"getaddrinfo({host!r})")
            raise NetworkBlocked(f"network access blocked in tests: lookup of {host!r}")
        return _real_getaddrinfo(host, *args, **kwargs)

    def guarded_connect(sock, address):
        if not _is_local_address(address):
            attempts.append(f"connect({address!r})")
            raise NetworkBlocked(f"network access blocked in tests: connect to {address!r}")
        return _real_connect(sock, address)

    def guarded_connect_ex(sock, address):
        if not _is_local_address(address):
            attempts.append(f"connect_ex({address!r})")
            raise NetworkBlocked(f"network access blocked in tests: connect to {address!r}")
        return _real_connect_ex(sock, address)

    def make_guarded_sock_connect(real):
        async def guarded_sock_connect(loop, sock, address):
            if not _is_local_address(address):
                attempts.append(f"sock_connect({address!r})")
                raise NetworkBlocked(f"network access blocked in tests: connect to {address!r}")
            return await real(loop, sock, address)

        return guarded_sock_connect

    for cls, real in _real_sock_connect.items():
        monkeypatch.setattr(cls, "sock_connect", make_guarded_sock_connect(real))
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    yield
    if attempts:
        pytest.fail(
            "test tried to reach the real network (mock the HTTP client instead): "
            + ", ".join(sorted(set(attempts))),
            pytrace=False,
        )


@pytest.fixture(autouse=True)
def _reset_ingest_rate_limit():
    """POST /api/ingest keeps a per-IP window in module state; every test starts with it empty."""
    mod = sys.modules.get("app.routes.realtime")
    if mod is not None:
        mod._ingest_rate_limit.clear()
        mod._INGEST_LAST_SEEN.clear()
    yield

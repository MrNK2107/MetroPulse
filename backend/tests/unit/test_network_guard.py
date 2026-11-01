"""The suite-wide network guard in tests/conftest.py."""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import pytest

from tests import conftest as guard

CONFTEST = Path(guard.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "host, local",
    [
        (None, True),
        ("", True),
        ("localhost", True),
        (b"localhost", True),
        ("127.0.0.1", True),
        ("127.5.5.5", True),
        ("::1", True),
        ("[::1]", True),
        ("news.google.com", False),
        (b"api.gdeltproject.org", False),
        ("8.8.8.8", False),
        ("10.0.0.1", False),
        ("2001:4860:4860::8888", False),
    ],
)
def test_is_local_host(host, local):
    assert guard._is_local_host(host) is local


def test_is_local_address_handles_tuples_and_unix_paths():
    assert guard._is_local_address(("127.0.0.1", 80))
    assert guard._is_local_address(("::1", 80, 0, 0))
    assert guard._is_local_address("/tmp/sock")
    assert not guard._is_local_address(("93.184.216.34", 443))


def test_loopback_is_still_allowed():
    # A listening loopback socket must keep working (asyncio's self-pipe, local servers).
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(server.getsockname())
    finally:
        client.close()
        server.close()


def _run_inner(tmp_path: Path, test_source: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (tmp_path / "test_inner.py").write_text(test_source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_inner.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_swallowed_network_error_still_fails_the_test(tmp_path):
    inner = '''
import socket

def test_swallows():
    try:
        socket.getaddrinfo("example.com", 443)
    except OSError:
        pass  # like the realtime connectors, which return None on any error
'''
    result = _run_inner(tmp_path, inner)
    assert result.returncode != 0, result.stdout
    assert "tried to reach the real network" in result.stdout
    assert "example.com" in result.stdout


def test_allow_network_marker_opts_out(tmp_path):
    inner = '''
import socket
import pytest

@pytest.mark.allow_network
def test_opted_out():
    assert socket.getaddrinfo.__module__ == "socket"
'''
    result = _run_inner(tmp_path, inner)
    assert result.returncode == 0, result.stdout

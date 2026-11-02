"""The locust file drives /ws/agent (the only socket) with a token from the environment.

Locust is not imported here: importing it monkeypatches the whole process with
gevent. The file is parsed instead, and its pure URL helper is compiled alone.
"""
from __future__ import annotations

import ast
from pathlib import Path

LOCUSTFILE = Path(__file__).resolve().parents[1] / "load" / "locustfile.py"


def _tree() -> ast.Module:
    return ast.parse(LOCUSTFILE.read_text(encoding="utf-8"))


def _helper(name: str):
    tree = _tree()
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[ast.ImportFrom("urllib.parse", [ast.alias("quote")], 0), fn], type_ignores=[])
    ns: dict = {}
    exec(compile(ast.fix_missing_locations(module), str(LOCUSTFILE), "exec"), ns)
    return ns[name]


def test_targets_agent_socket_not_retired_simulator():
    source = LOCUSTFILE.read_text(encoding="utf-8")
    assert "/ws/simulate" not in source
    assert "/ws/agent" in source
    assert "AGENT_WS_TOKEN" in source


def test_ws_url_from_host_and_token():
    ws_url = _helper("agent_ws_url")
    assert ws_url("http://localhost:8000", "t") == "ws://localhost:8000/ws/agent?token=t"
    assert ws_url("https://api.example.org/", "a b&c") == "wss://api.example.org/ws/agent?token=a%20b%26c"

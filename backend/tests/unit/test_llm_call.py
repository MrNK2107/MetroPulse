"""app.simulation.llm.call_llm: provider dispatch, request shape and timeouts (no network)."""
from __future__ import annotations

import asyncio
import json
import types

import httpx
import pytest

from app.simulation import llm


@pytest.fixture
def cfg(monkeypatch):
    s = llm.settings
    monkeypatch.setattr(s, "llm_provider", "mimo")
    monkeypatch.setattr(s, "llm_model", "")
    monkeypatch.setattr(s, "llm_timeout_ms", 25000)
    monkeypatch.setattr(s, "mimo_api_key", "test-mimo-key")
    monkeypatch.setattr(s, "mimo_base_url", "https://gateway.test/v1")
    monkeypatch.setattr(s, "ollama_base_url", "http://ollama.test:11434")
    monkeypatch.setattr(s, "openai_api_key", "test-openai-key")
    return s


@pytest.fixture
def transport(monkeypatch):
    """Route llm's httpx.AsyncClient through a MockTransport and record requests."""
    seen: list[httpx.Request] = []
    timeouts: list[float] = []
    handler_box = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler_box["fn"](request)

    real_client = httpx.AsyncClient

    def factory(timeout=None, **kw):
        timeouts.append(timeout)
        return real_client(transport=httpx.MockTransport(handler), timeout=timeout, **kw)

    monkeypatch.setattr(llm, "_httpx", types.SimpleNamespace(AsyncClient=factory))
    return types.SimpleNamespace(seen=seen, timeouts=timeouts, set=lambda fn: handler_box.update(fn=fn))


@pytest.mark.asyncio
async def test_mimo_request_shape(cfg, transport):
    transport.set(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":1}'}}]}))
    out = await llm.call_llm("hello")

    assert out == '{"ok":1}'
    req = transport.seen[0]
    assert str(req.url) == "https://gateway.test/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer test-mimo-key"
    body = json.loads(req.content)
    assert body["model"] == "mimo-v2.5-pro"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1] == {"role": "user", "content": "hello"}
    assert transport.timeouts == [25.0]


@pytest.mark.asyncio
async def test_ollama_request_shape_and_model_override(cfg, transport, monkeypatch):
    monkeypatch.setattr(cfg, "llm_provider", "ollama")
    monkeypatch.setattr(cfg, "llm_model", "llama3.2:3b")
    transport.set(lambda r: httpx.Response(200, json={"message": {"content": "pong"}}))
    out = await llm.call_llm("ping", provider="OLLAMA", timeout_ms=1500)

    assert out == "pong"
    req = transport.seen[0]
    assert str(req.url) == "http://ollama.test:11434/api/chat"
    body = json.loads(req.content)
    assert body == {"model": "llama3.2:3b", "messages": [{"role": "user", "content": "ping"}], "stream": False}
    assert transport.timeouts == [1.5]


@pytest.mark.asyncio
async def test_http_errors_propagate(cfg, transport):
    transport.set(lambda r: httpx.Response(502, json={"error": "bad gateway"}))
    with pytest.raises(httpx.HTTPStatusError):
        await llm.call_llm("hello")


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected(cfg):
    with pytest.raises(ValueError, match="Unsupported LLM provider: claude-pigeon"):
        await llm.call_llm("hello", provider="claude-pigeon")


@pytest.mark.asyncio
async def test_settings_provider_is_used_by_default(cfg, monkeypatch):
    calls = []

    async def fake(prompt, timeout_ms):
        calls.append((prompt, timeout_ms))
        return "gem"

    monkeypatch.setattr(cfg, "llm_provider", "Gemini")
    monkeypatch.setattr(llm, "_call_gemini", fake)
    assert await llm.call_llm("q") == "gem"
    assert calls == [("q", 25000)]


class _FakeCompletions:
    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        await asyncio.sleep(self.delay)
        msg = types.SimpleNamespace(content='{"type":"final"}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])


def _fake_openai(monkeypatch, completions):
    keys = []

    def ctor(api_key):
        keys.append(api_key)
        return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))

    monkeypatch.setattr(llm, "AsyncOpenAI", ctor)
    return keys


@pytest.mark.asyncio
async def test_openai_uses_json_mode_and_default_model(cfg, monkeypatch):
    completions = _FakeCompletions()
    keys = _fake_openai(monkeypatch, completions)
    out = await llm.call_llm("q", provider="openai")

    assert out == '{"type":"final"}'
    assert keys == ["test-openai-key"]
    assert completions.kwargs["model"] == "gpt-4o-mini"
    assert completions.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_llm_model_does_not_leak_into_an_overridden_provider(cfg, monkeypatch):
    # LLM_MODEL names a MiMo model; an explicit provider="openai" must not send it to OpenAI.
    monkeypatch.setattr(cfg, "llm_model", "mimo-v2.5-pro")
    completions = _FakeCompletions()
    _fake_openai(monkeypatch, completions)
    await llm.call_llm("q", provider="openai")
    assert completions.kwargs["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_openai_call_times_out(cfg, monkeypatch):
    _fake_openai(monkeypatch, _FakeCompletions(delay=1.0))
    with pytest.raises(asyncio.TimeoutError):
        await llm.call_llm("q", provider="openai", timeout_ms=20)

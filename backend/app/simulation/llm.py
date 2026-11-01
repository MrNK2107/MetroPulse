from __future__ import annotations

import asyncio
import logging

import httpx as _httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "mimo": "mimo-v2.5-pro",
    "ollama": "gemma4:latest",
}


def _model(provider: str) -> str:
    """LLM_MODEL applies to the configured provider; an explicit other provider gets its default."""
    if provider == settings.llm_provider.lower():
        return settings.resolved_llm_model
    return _DEFAULT_MODELS[provider]


async def call_llm(prompt: str, provider: str | None = None, timeout_ms: int | None = None) -> str:
    """Unified LLM caller — injected into the engine via the ``llm_fn`` callback."""
    provider = (provider or settings.llm_provider).lower()
    timeout_ms = timeout_ms or settings.llm_timeout_ms

    if provider == "gemini":
        return await _call_gemini(prompt, timeout_ms)
    elif provider == "openai":
        return await _call_openai(prompt, timeout_ms)
    elif provider == "mimo":
        return await _call_mimo(prompt, timeout_ms)
    elif provider == "ollama":
        return await _call_ollama(prompt, timeout_ms)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


async def _call_gemini(prompt: str, timeout_ms: int) -> str:
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await asyncio.wait_for(
        asyncio.to_thread(
            client.models.generate_content,
            model=_model("gemini"),
            contents=prompt,
        ),
        timeout=timeout_ms / 1000.0,
    )
    return response.text


async def _call_openai(prompt: str, timeout_ms: int) -> str:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=_model("openai"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        ),
        timeout=timeout_ms / 1000.0,
    )
    return response.choices[0].message.content


async def _call_mimo(prompt: str, timeout_ms: int) -> str:
    headers = {
        "Authorization": f"Bearer {settings.mimo_api_key}",
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
    }
    body = {
        "model": _model("mimo"),
        "messages": [
            {"role": "system", "content": "You are a JSON-only API. Respond with valid JSON only, no markdown fences."},
            {"role": "user", "content": prompt},
        ],
    }
    async with _httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
        resp = await client.post(
            f"{settings.mimo_base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_ollama(prompt: str, timeout_ms: int) -> str:
    headers = {"Content-Type": "application/json"}
    body = {
        "model": _model("ollama"),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    async with _httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]

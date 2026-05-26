"""Path 3: Local LLM fallback via Ollama (optional)."""
from __future__ import annotations

import json
import logging
from typing import Any

from engine.models import ParsedScenario, SECTOR_NAMES
from engine.nl_engine.domain_maps import CITY_ALIASES, SECTOR_SYNONYMS

logger = logging.getLogger(__name__)

PARSER_PROMPT = """You are an economic scenario parser. Given a user's text, extract structured parameters.

User text: "{text}"

Extract as JSON:
{{
  "city": "city name or null",
  "sectors": [
    {{"name": "sector_name", "delta": number}}
  ],
  "policies": ["policy_name"],
  "events": ["event_name"],
  "horizon_months": number
}}

Valid sectors: it_ites, manufacturing, real_estate, trade_hospitality, transport_logistics, informal, public_admin
Valid policies: sez, smart_city, amrut, rera, pm_awas, make_in_india, digital_india
Valid events: fuel_price_hike, heavy_rainfall, drought, interest_rate_hike, subsidy_added, unemployment_rise, pandemic

Respond with only the JSON object."""


class OllamaParser:
    """Ollama-based parser for complex/ambiguous inputs."""

    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url

    async def parse(self, text: str) -> ParsedScenario:
        """Parse text using local Ollama model. Falls back to empty result if unavailable."""
        try:
            response = await self._call_ollama(text)
            return self._parse_response(response, text)
        except Exception as e:
            logger.warning("Ollama parse failed: %s", e)
            return self._fallback_result(text)

    async def _call_ollama(self, text: str) -> str:
        """Call Ollama API. Raises if not available."""
        import httpx

        prompt = PARSER_PROMPT.format(text=text)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    def _parse_response(self, response: str, original_text: str) -> ParsedScenario:
        """Parse Ollama JSON response into ParsedScenario."""
        try:
            json_str = response
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse Ollama response as JSON")
            return self._fallback_result(original_text)

        city_raw = (data.get("city") or "").lower().strip()
        city = CITY_ALIASES.get(city_raw, city_raw if city_raw else "")

        sector_deltas = {s: 0.0 for s in SECTOR_NAMES}
        for sector_info in data.get("sectors", []):
            name = sector_info.get("name", "")
            delta = float(sector_info.get("delta", 0))
            if name in SECTOR_NAMES:
                sector_deltas[name] = max(-50.0, min(50.0, delta))

        policies = data.get("policies", [])

        horizon = int(data.get("horizon_months", 24))
        horizon = min([6, 12, 24, 60], key=lambda x: abs(x - horizon))

        keywords = [city] + [s for s, d in sector_deltas.items() if d != 0] + policies

        return ParsedScenario(
            city=city,
            sector_deltas=sector_deltas,
            policies_active=policies,
            public_works_zone=None,
            horizon_months=horizon,
            causal_chain=original_text.strip(),
            keywords=[k for k in keywords if k],
            confidence="medium",
            assumptions=["Parsed via local LLM. Verify parameters."],
        )

    def _fallback_result(self, text: str) -> ParsedScenario:
        """Return empty result when Ollama is unavailable."""
        return ParsedScenario(
            city="",
            sector_deltas={s: 0.0 for s in SECTOR_NAMES},
            policies_active=[],
            public_works_zone=None,
            horizon_months=24,
            causal_chain=text.strip(),
            keywords=[],
            confidence="low",
            assumptions=["Could not parse scenario. Please try rephrasing."],
        )

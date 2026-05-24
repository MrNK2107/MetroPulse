from __future__ import annotations

import re

from engine.config import CityConfig, list_available_cities
from engine.models import ParsedScenario, SECTOR_NAMES, SECTOR_LABELS


CITY_ALIASES: dict[str, str] = {
    "bangalore": "bengaluru",
    "bengaluru": "bengaluru",
    "bombay": "mumbai",
    "mumbai": "mumbai",
    "delhi": "delhi_ncr",
    "ncr": "delhi_ncr",
    "delhi ncr": "delhi_ncr",
    "hyderabad": "hyderabad",
    "chennai": "chennai",
    "pune": "pune",
    "kolkata": "kolkata",
    "calcutta": "kolkata",
    "ahmedabad": "ahmedabad",
    "jaipur": "jaipur",
    "lucknow": "lucknow",
    "chandigarh": "chandigarh",
    "bhubaneswar": "bhubaneswar",
}

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "it_ites": ["it", "tech", "software", "startup", "digital", "ites"],
    "manufacturing": ["manufacturing", "factory", "auto", "pharma", "textile", "industrial"],
    "real_estate": ["real estate", "housing", "construction", "property", "rent"],
    "trade_hospitality": ["trade", "retail", "hospitality", "tourism", "hotel"],
    "transport_logistics": ["transport", "logistics", "metro", "port", "rail", "freight"],
    "informal": ["informal", "street vendor", "slum", "casual labor"],
    "public_admin": ["public administration", "government", "municipal", "civic"],
}

POLICY_KEYWORDS: dict[str, list[str]] = {
    "SEZ Notification": ["sez", "special economic zone"],
    "Smart City Mission": ["smart city"],
    "AMRUT": ["amrut", "water", "sanitation"],
    "RERA Compliance": ["rera"],
    "PM Awas Yojana": ["pmay", "awas", "affordable housing", "housing scheme"],
    "Make in India": ["make in india"],
    "Digital India": ["digital india"],
}


class ScenarioParseError(ValueError):
    pass


async def parse_scenario(text: str) -> ParsedScenario:
    return _fallback_parse(text)


def resolve_city_id(value: str) -> str:
    needle = _clean(value)
    if needle in CITY_ALIASES:
        return CITY_ALIASES[needle]
    for city in list_available_cities():
        if needle in {_clean(city["id"]), _clean(city["name"])}:
            return city["id"]
    raise ScenarioParseError("I could not identify the city. Try naming one Indian city, for example Hyderabad or Bengaluru.")


def build_params(parsed: ParsedScenario):
    from engine.models import SimulationParams

    cfg = CityConfig.load(parsed.city)
    return SimulationParams(
        city=parsed.city,
        sector_deltas={sector: float(parsed.sector_deltas.get(sector, 0.0)) for sector in SECTOR_NAMES},
        policies_active=parsed.policies_active,
        public_works_zone=parsed.public_works_zone,
        horizon_months=parsed.horizon_months,
        city_config=cfg,
        assumptions=parsed.assumptions,
    )


def _fallback_parse(text: str) -> ParsedScenario:
    lowered = text.lower()
    city = _extract_city(lowered)
    if city is None:
        raise ScenarioParseError("I could not identify the city. Try: 'What happens to Hyderabad if pharma FDI drops 40%?'")

    sector_deltas = {sector: 0.0 for sector in SECTOR_NAMES}
    mentioned_sectors: list[str] = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(_contains_keyword(lowered, keyword) for keyword in keywords):
            mentioned_sectors.append(sector)
            sector_deltas[sector] = _infer_delta(lowered, keywords)

    policies = [
        policy
        for policy, keywords in POLICY_KEYWORDS.items()
        if any(_contains_keyword(lowered, keyword) for keyword in keywords)
    ]

    horizon, horizon_was_explicit = _extract_horizon(lowered)
    assumptions = []
    if not horizon_was_explicit:
        assumptions.append("Time horizon defaulted to 24 months because the prompt did not specify duration.")

    if not mentioned_sectors and not policies:
        if any(word in lowered for word in ["boom", "growth", "investment", "improve"]):
            sector_deltas["it_ites"] = 25.0
            sector_deltas["manufacturing"] = 10.0
            mentioned_sectors = ["it_ites", "manufacturing"]
            assumptions.append("Vague growth prompt interpreted as broad IT and manufacturing investment.")
        elif any(word in lowered for word in ["crisis", "shock", "recession", "drop", "decline"]):
            sector_deltas["it_ites"] = -15.0
            sector_deltas["trade_hospitality"] = -10.0
            mentioned_sectors = ["it_ites", "trade_hospitality"]
            assumptions.append("Vague negative prompt interpreted as a broad urban demand shock.")
        else:
            raise ScenarioParseError("The prompt names a city but not a change to simulate. Add a sector, policy, or shock.")

    keywords = [city, *mentioned_sectors, *policies]
    return ParsedScenario(
        city=city,
        sector_deltas=sector_deltas,
        policies_active=policies,
        public_works_zone=None,
        horizon_months=horizon,
        causal_chain=text.strip(),
        keywords=keywords,
        confidence="medium" if assumptions else "high",
        assumptions=assumptions or ["Scenario parsed from explicit city, sector, policy, and/or percentage cues."],
    )


def _extract_city(text: str) -> str | None:
    for alias, city_id in CITY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return city_id
    return None


def _infer_delta(text: str, keywords: list[str]) -> float:
    percent_match = re.search(r"([+-]?\d{1,3})\s*%", text)
    magnitude = float(percent_match.group(1)) if percent_match else 25.0
    if magnitude > 100:
        magnitude = 100.0

    negative_words = ["drop", "drops", "decline", "falls", "fall", "cut", "loss", "crisis", "shock", "reduce", "reduced"]
    positive_words = ["increase", "increases", "rise", "rises", "boom", "growth", "boost", "push", "investment", "improve"]
    if any(word in text for word in negative_words):
        return -abs(magnitude)
    if any(word in text for word in positive_words):
        return abs(magnitude)
    return magnitude if any(_contains_keyword(text, keyword) for keyword in keywords) else 0.0


def _extract_horizon(text: str) -> tuple[int, bool]:
    match = re.search(r"(\d{1,2})\s*(month|months|m)\b", text)
    if match:
        value = int(match.group(1))
        return min([6, 12, 24, 60], key=lambda x: abs(x - value)), True
    match = re.search(r"(\d)\s*(year|years|yr|yrs)\b", text)
    if match:
        value = int(match.group(1)) * 12
        return min([6, 12, 24, 60], key=lambda x: abs(x - value)), True
    return 24, False


def _contains_keyword(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _clean(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

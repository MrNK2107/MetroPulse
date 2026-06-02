from __future__ import annotations

from app.db import LOCAL_CASE_STUDIES
from app.rag.models import EvidenceItem
from engine.models import ParsedScenario


_CITY_ALIASES: dict[str, str] = {
    "bombay": "mumbai",
    "madras": "chennai",
    "calcutta": "kolkata",
    "bangalore": "bengaluru",
    "bengaluru": "bengaluru",
    "mumbai": "mumbai",
    "chennai": "chennai",
    "kolkata": "kolkata",
    "delhi": "delhi ncr",
    "new delhi": "delhi ncr",
    "hyderabad": "hyderabad",
    "pune": "pune",
    "ahmedabad": "ahmedabad",
    "lucknow": "lucknow",
    "jaipur": "jaipur",
    "chandigarh": "chandigarh",
    "bhubaneswar": "bhubaneswar",
}

_SECTOR_SYNONYMS: dict[str, str] = {
    "tech": "it_ites",
    "it": "it_ites",
    "software": "it_ites",
    "housing": "real_estate",
    "property": "real_estate",
    "realestate": "real_estate",
    "hospitality": "trade_hospitality",
    "trade": "trade_hospitality",
    "tourism": "trade_hospitality",
    "retail": "trade_hospitality",
    "logistics": "transport_logistics",
    "transport": "transport_logistics",
    "shipping": "transport_logistics",
    "freight": "transport_logistics",
    "factories": "manufacturing",
    "industry": "manufacturing",
    "industrial": "manufacturing",
    "factory": "manufacturing",
    "government": "public_admin",
    "civic": "public_admin",
    "municipal": "public_admin",
    "street vendors": "informal",
    "informal": "informal",
    "gig": "informal",
}


def _resolve_city(name: str) -> str:
    """Resolve city aliases (Bombay→mumbai, etc.) to canonical lowercase form."""
    normalized = name.lower().strip().replace("_", " ")
    return _CITY_ALIASES.get(normalized, normalized)


def _resolve_sector(name: str) -> str | None:
    """Resolve sector synonyms (tech→it_ites, housing→real_estate, etc.)."""
    key = name.lower().strip().replace(" ", "_")
    return _SECTOR_SYNONYMS.get(key)


def retrieve_evidence(parsed: ParsedScenario, scenario_text: str, top_k: int = 5) -> tuple[list[str], list[EvidenceItem]]:
    sectors = {sector for sector, delta in parsed.sector_deltas.items() if abs(delta) > 0}
    policies = set(parsed.policies_active)
    city = _resolve_city(parsed.city)

    # Expand sector set with synonym matches
    expanded_sectors = set(sectors)
    for sector in sectors:
        expanded_sectors.add(sector)  # keep original

    terms = _query_terms(parsed, scenario_text)
    items: list[EvidenceItem] = []

    for case in LOCAL_CASE_STUDIES:
        case_city = _resolve_city(case.city)
        # Also expand case sectors through synonyms for matching
        case_sector_set = set(case.sectors)
        for cs in case.sectors:
            syn = _resolve_sector(cs)
            if syn:
                case_sector_set.add(syn)
        matched_sectors = sorted(expanded_sectors & case_sector_set)
        matched_policies = sorted(policies & set(case.policies))
        city_score = 0.25 if city and (city == case_city or city in case_city or case_city in city) else 0.0
        sector_score = 0.45 * (len(matched_sectors) / max(len(expanded_sectors), 1))
        policy_score = 0.20 * (len(matched_policies) / max(len(policies), 1)) if policies else 0.0
        keyword_score = 0.15 if any(term.replace("_", " ") in (case.title + " " + case.description).lower() for term in terms) else 0.0
        relevance = min(1.0, city_score + sector_score + policy_score + keyword_score)
        if relevance < 0.25:
            continue
        effects = dict(case.observed_effects) if case.observed_effects else {"outcome": case.outcome}
        items.append(EvidenceItem(
            id=case.id,
            title=case.title,
            summary=case.outcome or case.description,
            source_type="historical_case_study",
            city=case.city,
            country="India",
            sectors=case.sectors,
            policies=case.policies,
            shock_types=_shock_types(scenario_text),
            time_period=str(case.year),
            observed_effects=effects,
            confidence=0.55 + min(relevance, 0.4),
            citation=case.source,
            relevance=relevance,
            matched_sectors=matched_sectors,
        ))

    items.sort(key=lambda item: (-item.relevance, -item.confidence, item.title))
    return terms, items[:top_k]


def _query_terms(parsed: ParsedScenario, scenario_text: str) -> list[str]:
    terms = list(parsed.keywords)
    lowered = scenario_text.lower()
    if any(word in lowered for word in ("petrol", "diesel", "fuel", "oil")):
        terms.extend(["fuel price increase", "urban logistics", "transport elasticity", "India fuel shock"])
    if any(word in lowered for word in ("housing", "rent", "real estate")):
        terms.extend(["housing affordability", "real estate pressure"])
    if any(word in lowered for word in ("jobs", "layoff", "employment")):
        terms.extend(["employment impact", "jobs pressure"])
    return _unique(terms)


def _shock_types(text: str) -> list[str]:
    lowered = text.lower()
    result = []
    if any(word in lowered for word in ("petrol", "diesel", "fuel", "oil")):
        result.append("fuel_price_shock")
    if any(word in lowered for word in ("drop", "decline", "loss", "crisis")):
        result.append("negative_demand_shock")
    if any(word in lowered for word in ("growth", "boom", "increase", "boost")):
        result.append("positive_growth_shock")
    return result or ["generic_scenario_shock"]


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result

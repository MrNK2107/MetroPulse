from __future__ import annotations

from app.db import LOCAL_CASE_STUDIES
from app.rag.models import EvidenceItem
from engine.models import ParsedScenario


def retrieve_evidence(parsed: ParsedScenario, scenario_text: str, top_k: int = 5) -> tuple[list[str], list[EvidenceItem]]:
    sectors = {sector for sector, delta in parsed.sector_deltas.items() if abs(delta) > 0}
    policies = set(parsed.policies_active)
    city = parsed.city.lower().replace("_", " ")
    terms = _query_terms(parsed, scenario_text)
    items: list[EvidenceItem] = []

    for case in LOCAL_CASE_STUDIES:
        case_city = case.city.lower()
        matched_sectors = sorted(sectors & set(case.sectors))
        matched_policies = sorted(policies & set(case.policies))
        city_score = 0.25 if city and city in case_city else 0.0
        sector_score = 0.45 * (len(matched_sectors) / max(len(sectors), 1))
        policy_score = 0.20 * (len(matched_policies) / max(len(policies), 1)) if policies else 0.0
        keyword_score = 0.10 if any(term.replace("_", " ") in (case.title + " " + case.description).lower() for term in terms) else 0.0
        relevance = min(1.0, city_score + sector_score + policy_score + keyword_score)
        if relevance < 0.25:
            continue
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
            observed_effects={"outcome": case.outcome},
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

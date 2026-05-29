from __future__ import annotations

from app.rag.models import EvidenceCoverage, EvidencePack
from app.rag.retriever import retrieve_evidence
from engine.models import ParsedScenario


def build_evidence_pack(parsed: ParsedScenario, scenario_text: str) -> EvidencePack:
    query_terms, items = retrieve_evidence(parsed, scenario_text)
    sectors = {sector for sector, delta in parsed.sector_deltas.items() if abs(delta) > 0}
    policies = set(parsed.policies_active)
    city = parsed.city.lower().replace("_", " ")
    city_matches = sum(1 for item in items if item.city and city in item.city.lower())
    sector_matches = sum(1 for item in items if sectors & set(item.sectors))
    policy_matches = sum(1 for item in items if policies & set(item.policies))

    coverage = EvidenceCoverage(
        city_match="strong" if city_matches >= 2 else "partial" if city_matches else "none",
        sector_match="strong" if sector_matches >= max(2, len(items) // 2) else "medium" if sector_matches else "none",
        policy_match="strong" if policies and policy_matches >= 2 else "medium" if policy_matches else "none",
        evidence_count=len(items),
    )
    overall = 0.0
    if items:
        avg_conf = sum(item.confidence * item.relevance for item in items) / max(sum(item.relevance for item in items), 0.01)
        coverage_bonus = 0.05 if coverage.city_match != "none" else 0.0
        overall = min(0.95, avg_conf + coverage_bonus)

    return EvidencePack(
        scenario=scenario_text,
        query_terms=query_terms,
        items=items,
        coverage=coverage,
        overall_evidence_confidence=round(overall, 3),
    )

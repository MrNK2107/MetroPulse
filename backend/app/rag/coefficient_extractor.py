from __future__ import annotations

from app.rag.models import CoefficientAdjustment, EvidencePack


def extract_coefficient_adjustments(
    sector_deltas: dict[str, float],
    evidence_pack: EvidencePack,
) -> dict[str, CoefficientAdjustment]:
    adjustments: dict[str, CoefficientAdjustment] = {}
    for sector, delta in sector_deltas.items():
        if abs(delta) <= 0:
            continue
        baseline = float(delta) / 100.0
        matched = [item for item in evidence_pack.items if sector in item.sectors]
        if matched:
            evidence_strength = sum(item.relevance * item.confidence for item in matched) / len(matched)
            factor = _clamp(0.65 + evidence_strength * 0.35, 0.65, 1.10)
            confidence = _clamp(evidence_pack.overall_evidence_confidence * 0.85 + 0.10, 0.0, 0.90)
            sources = [item.title for item in matched[:3]]
            reasoning = "Evidence supports this sector direction; magnitude is bounded by available case relevance."
        else:
            factor = 0.75
            confidence = 0.35
            sources = []
            reasoning = "No close evidence matched this sector, so the baseline coefficient is dampened."
        adjusted = _clamp(baseline * factor, -0.75, 0.75)
        adjustments[sector] = CoefficientAdjustment(
            sector=sector,
            baseline_coefficient=baseline,
            evidence_adjusted_coefficient=adjusted,
            confidence=round(confidence, 3),
            sources=sources,
            reasoning=reasoning,
        )
    return adjustments


def coefficient_factors(adjustments: dict[str, CoefficientAdjustment]) -> dict[str, float]:
    factors = {}
    for sector, adj in adjustments.items():
        if abs(adj.baseline_coefficient) < 1e-9:
            continue
        factors[sector] = adj.evidence_adjusted_coefficient / adj.baseline_coefficient
    return factors


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))

"""Post-simulation social group impact scoring."""
from __future__ import annotations

from dataclasses import dataclass

from engine.models import AggregateMetrics, SECTOR_NAMES
from engine.nl_engine.domain_maps import SOCIAL_GROUPS


@dataclass
class GroupImpact:
    """Impact metrics for a single social group."""
    name: str
    purchasing_power: float
    income_stability: float
    expense_pressure: float
    housing_impact: float
    employment_impact: float
    severity: str  # "low" | "moderate" | "high"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "purchasing_power": self.purchasing_power,
            "income_stability": self.income_stability,
            "expense_pressure": self.expense_pressure,
            "housing_impact": self.housing_impact,
            "employment_impact": self.employment_impact,
            "severity": self.severity,
        }


def classify_severity(purchasing_power: float, employment_impact: float) -> str:
    """Classify impact severity based on purchasing power and employment."""
    combined = abs(purchasing_power) + abs(employment_impact)
    if combined >= 15:
        return "high"
    if combined >= 7:
        return "moderate"
    return "low"


def weighted_avg(values: list[float], weights: list[float]) -> float:
    """Compute weighted average. Returns 0 if inputs are empty."""
    if not values:
        return 0.0
    total_weight = sum(weights)
    if total_weight == 0:
        return sum(values) / len(values)
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def score_groups(
    sector_deltas: dict[str, float],
    metrics: AggregateMetrics,
) -> list[GroupImpact]:
    """Compute per-group impacts from simulation results."""
    results = []

    for group_name, group_def in SOCIAL_GROUPS.items():
        # Income: weighted average of income sector deltas
        income_values = [sector_deltas.get(s, 0.0) for s in group_def["income_sectors"]]
        income_weights = [group_def["sensitivity"].get(s, 0.5) for s in group_def["income_sectors"]]
        income_delta = weighted_avg(income_values, income_weights)

        # Expenses: weighted average of expense sector deltas (inverted)
        expense_values = [sector_deltas.get(s, 0.0) for s in group_def["expense_sectors"]]
        expense_weights = [group_def["sensitivity"].get(s, 0.5) for s in group_def["expense_sectors"]]
        expense_delta = weighted_avg(expense_values, expense_weights)

        purchasing_power = income_delta - expense_delta
        housing_impact = (metrics.realEstateIndex - 1.0) * 100
        employment_impact = metrics.unemploymentRate

        results.append(GroupImpact(
            name=group_name,
            purchasing_power=round(purchasing_power, 1),
            income_stability=round(income_delta, 1),
            expense_pressure=round(expense_delta, 1),
            housing_impact=round(housing_impact, 1),
            employment_impact=round(employment_impact, 1),
            severity=classify_severity(purchasing_power, employment_impact),
        ))

    return results


def compute_satisfaction(groups: list[GroupImpact]) -> int:
    """Compute citizen satisfaction score (0-100) from group impacts."""
    satisfaction = 50.0
    for g in groups:
        group_def = SOCIAL_GROUPS.get(g.name, {})
        weight = group_def.get("population_weight", 0.05)
        satisfaction += g.purchasing_power * weight * 0.5
        satisfaction += (100 - abs(g.employment_impact * 10)) * weight * 0.3
    return max(0, min(100, round(satisfaction)))

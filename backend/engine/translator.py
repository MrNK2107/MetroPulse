"""Translate simulation results into plain-language impacts.

Converts raw sector deltas and aggregate metrics into relatable,
rupee-denominated impact descriptions that non-experts can understand.
Deterministic — no LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.models import AggregateMetrics, SECTOR_LABELS, SECTOR_NAMES
from engine.nl_engine.domain_maps import SECTOR_SYNONYMS, SOCIAL_GROUPS

# National-average cost proxies (₹). Used to compute per-person impacts.
COST_PROXIES: dict[str, float] = {
    "auto_daily_fuel": 450.0,
    "avg_monthly_rent_2bhk": 15000.0,
    "small_shop_daily_revenue": 8000.0,
    "street_vendor_daily_income": 500.0,
    "it_avg_monthly_salary": 65000.0,
    "factory_worker_monthly_wage": 18000.0,
    "govt_contract_monthly": 22000.0,
    "delivery_daily_cost": 200.0,
}

# Reverse lookup: sector → keywords a user might have used
SECTOR_TO_KEYWORDS: dict[str, list[str]] = {
    "transport_logistics": ["petrol", "diesel", "fuel", "auto", "bus", "taxi", "delivery", "commute"],
    "it_ites": ["tech", "software", "IT", "startup", "office"],
    "manufacturing": ["factory", "industrial", "production", "plant"],
    "real_estate": ["rent", "housing", "property", "home", "apartment"],
    "trade_hospitality": ["shop", "restaurant", "retail", "tourism", "hotel"],
    "informal": ["street vendor", "daily wage", "gig", "hawker"],
    "public_admin": ["government", "govt", "public sector", "contract"],
}


@dataclass
class SectorImpact:
    """Plain-language impact for a single sector."""
    sector: str
    sector_label: str
    delta_pct: float
    direction: str  # "positive" | "negative" | "mixed"
    headline: str
    person_example: str
    city_wide: str
    numbers: dict[str, float] = field(default_factory=dict)
    # Provenance
    origin: str = "estimated"  # "real" | "estimated" | "synthetic"
    confidence: float = 0.55
    sources: list[str] = field(default_factory=list)


@dataclass
class TranslationResult:
    """Full plain-language translation of simulation results."""
    headline: str
    sector_impacts: list[SectorImpact]
    takeaways: list[str]
    gdp_summary: str
    unemployment_summary: str
    overall_verdict: str
    affected_groups: list[dict[str, Any]] = field(default_factory=list)
    # Provenance
    confidence: float = 0.55
    confidence_label: str = "Medium"
    origin: str = "estimated"
    limitations: list[str] = field(default_factory=list)


def _per_capita_gdp(city_config: Any) -> float:
    """Per-capita GDP in rupees from city config."""
    gdp_crores = city_config.baselines.get("gdp_estimate_crores", 100000)
    pop = max(city_config.population, 1)
    return (gdp_crores * 1e7) / pop


def _jobs_in_sector(city_config: Any, sector: str) -> int:
    """Estimate total jobs in a sector from city baselines."""
    weight = city_config.sector_weights.get(sector, 0.1)
    formal = city_config.baselines.get("employment_formal", 1_000_000)
    informal = city_config.baselines.get("employment_informal", 500_000)
    # Use formal for formal sectors, mix for informal
    if sector == "informal":
        return int(informal * 0.6)
    return int(formal * weight)


def _compute_jobs_at_risk(city_config: Any, sector: str, delta_pct: float) -> int:
    """Compute number of jobs at risk from a sector delta."""
    weight = city_config.sector_weights.get(sector, 0.1)
    formal = city_config.baselines.get("employment_formal", 1_000_000)
    return int(formal * weight * abs(delta_pct) / 100)


def _find_user_keyword(original_query: str, sector: str) -> str | None:
    """Find which keyword from the user's query maps to this sector."""
    lowered = original_query.lower()
    keywords = SECTOR_TO_KEYWORDS.get(sector, [])
    for kw in keywords:
        if kw.lower() in lowered:
            return kw
    # Also check SECTOR_SYNONYMS reverse lookup
    for synonym, mapped_sector in SECTOR_SYNONYMS.items():
        if mapped_sector == sector and synonym in lowered:
            return synonym
    return None


def _translate_transport(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate transport & logistics delta to plain language."""
    abs_delta = abs(delta_pct)
    daily_fuel = COST_PROXIES["auto_daily_fuel"] * abs_delta / 100
    jobs = _jobs_in_sector(city_config, "transport_logistics")
    jobs_affected = int(jobs * abs_delta / 100)
    delivery_cost = COST_PROXIES["delivery_daily_cost"] * abs_delta / 100

    if delta_pct < 0:
        return SectorImpact(
            sector="transport_logistics",
            sector_label="Transport & Daily Commute",
            delta_pct=delta_pct,
            direction="negative",
            headline="Transport costs go up",
            person_example=(
                f"Auto-rickshaw and taxi drivers pay about \u20b9{daily_fuel:.0f} more per day for fuel. "
                f"Delivery costs rise roughly \u20b9{delivery_cost:.0f} per trip."
            ),
            city_wide=(
                f"City-wide, roughly {jobs_affected:,} transport jobs are under pressure. "
                f"Bus fares and delivery charges may increase for everyone."
            ),
            numbers={
                "daily_fuel_increase": round(daily_fuel),
                "jobs_affected": jobs_affected,
                "delivery_cost_increase": round(delivery_cost),
            },
        )
    else:
        return SectorImpact(
            sector="transport_logistics",
            sector_label="Transport & Daily Commute",
            delta_pct=delta_pct,
            direction="positive",
            headline="Transport sector grows",
            person_example=(
                f"Auto and taxi drivers may earn about \u20b9{daily_fuel:.0f} more per day "
                f"from increased demand."
            ),
            city_wide=f"About {jobs_affected:,} new transport-related jobs expected.",
            numbers={"daily_income_boost": round(daily_fuel), "new_jobs": jobs_affected},
        )


def _translate_it(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate IT/ITES delta to plain language."""
    abs_delta = abs(delta_pct)
    jobs = _jobs_in_sector(city_config, "it_ites")
    jobs_count = int(jobs * abs_delta / 100)
    salary_impact = COST_PROXIES["it_avg_monthly_salary"] * abs_delta / 100
    rent_impact = COST_PROXIES["avg_monthly_rent_2bhk"] * (abs_delta / 100) * 0.3

    if delta_pct > 0:
        return SectorImpact(
            sector="it_ites",
            sector_label="IT & Tech Jobs",
            delta_pct=delta_pct,
            direction="positive",
            headline="Tech sector booms",
            person_example=(
                f"About {jobs_count:,} new tech jobs expected. "
                f"Average tech salary may go up roughly \u20b9{salary_impact:,.0f}/month."
            ),
            city_wide=(
                f"Rents in IT corridors may rise about \u20b9{rent_impact:,.0f}/month "
                f"for a typical 2BHK as more workers move in."
            ),
            numbers={
                "new_jobs": jobs_count,
                "salary_boost_monthly": round(salary_impact),
                "rent_increase_monthly": round(rent_impact),
            },
        )
    else:
        return SectorImpact(
            sector="it_ites",
            sector_label="IT & Tech Jobs",
            delta_pct=delta_pct,
            direction="negative",
            headline="Tech sector slows down",
            person_example=(
                f"About {jobs_count:,} tech jobs at risk. "
                f"Average tech salary may drop roughly \u20b9{salary_impact:,.0f}/month."
            ),
            city_wide=(
                f"IT corridor rents may drop about \u20b9{abs(rent_impact):,.0f}/month "
                f"as fewer workers need housing."
            ),
            numbers={
                "jobs_at_risk": jobs_count,
                "salary_drop_monthly": round(abs(salary_impact)),
                "rent_drop_monthly": round(abs(rent_impact)),
            },
        )


def _translate_manufacturing(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate manufacturing delta to plain language."""
    abs_delta = abs(delta_pct)
    jobs = _jobs_in_sector(city_config, "manufacturing")
    jobs_count = int(jobs * abs_delta / 100)
    wage_impact = COST_PROXIES["factory_worker_monthly_wage"] * abs_delta / 100

    if delta_pct < 0:
        return SectorImpact(
            sector="manufacturing",
            sector_label="Manufacturing & Factories",
            delta_pct=delta_pct,
            direction="negative",
            headline="Factory jobs at risk",
            person_example=(
                f"Factory workers face potential layoffs \u2014 about {jobs_count:,} "
                f"manufacturing jobs at risk. Workers may lose \u20b9{abs(wage_impact):,.0f}/month."
            ),
            city_wide=(
                f"Industrial area rents and demand for raw materials may drop "
                f"as production slows."
            ),
            numbers={
                "jobs_at_risk": jobs_count,
                "wage_loss_monthly": round(abs(wage_impact)),
            },
        )
    else:
        return SectorImpact(
            sector="manufacturing",
            sector_label="Manufacturing & Factories",
            delta_pct=delta_pct,
            direction="positive",
            headline="Manufacturing expands",
            person_example=(
                f"About {jobs_count:,} new factory jobs expected. "
                f"Workers may earn \u20b9{wage_impact:,.0f}/month more."
            ),
            city_wide="Industrial areas see more activity and demand for workers.",
            numbers={"new_jobs": jobs_count, "wage_boost_monthly": round(wage_impact)},
        )


def _translate_real_estate(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate real estate delta to plain language."""
    abs_delta = abs(delta_pct)
    rent_impact = COST_PROXIES["avg_monthly_rent_2bhk"] * abs_delta / 100

    if delta_pct > 0:
        return SectorImpact(
            sector="real_estate",
            sector_label="Rent & Housing",
            delta_pct=delta_pct,
            direction="positive",
            headline="Rents and property prices go up",
            person_example=(
                f"Monthly rent may go up about \u20b9{rent_impact:,.0f} "
                f"in affected areas for a typical 2BHK."
            ),
            city_wide=(
                f"Home prices shift roughly {abs_delta:.0f}%. "
                f"Tenants face higher costs; landlords benefit."
            ),
            numbers={"rent_increase_monthly": round(rent_impact), "price_shift_pct": abs_delta},
        )
    else:
        return SectorImpact(
            sector="real_estate",
            sector_label="Rent & Housing",
            delta_pct=delta_pct,
            direction="negative",
            headline="Rents and property prices drop",
            person_example=(
                f"Monthly rent may drop about \u20b9{abs(rent_impact):,.0f} "
                f"in affected areas."
            ),
            city_wide=(
                f"Home prices shift roughly {abs_delta:.0f}%. "
                f"Tenants benefit; landlords and builders face pressure."
            ),
            numbers={"rent_drop_monthly": round(abs(rent_impact)), "price_shift_pct": abs_delta},
        )


def _translate_trade(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate trade & hospitality delta to plain language."""
    abs_delta = abs(delta_pct)
    daily_loss = COST_PROXIES["small_shop_daily_revenue"] * abs_delta / 100
    jobs = _jobs_in_sector(city_config, "trade_hospitality")
    jobs_count = int(jobs * abs_delta / 100)

    if delta_pct < 0:
        return SectorImpact(
            sector="trade_hospitality",
            sector_label="Shops, Restaurants & Tourism",
            delta_pct=delta_pct,
            direction="negative",
            headline="Local businesses earn less",
            person_example=(
                f"Small shops earn about \u20b9{daily_loss:,.0f} less per day. "
                f"Restaurant footfall drops around {abs_delta:.0f}%."
            ),
            city_wide=f"About {jobs_count:,} retail and hospitality jobs at risk.",
            numbers={
                "daily_revenue_loss": round(daily_loss),
                "jobs_at_risk": jobs_count,
            },
        )
    else:
        return SectorImpact(
            sector="trade_hospitality",
            sector_label="Shops, Restaurants & Tourism",
            delta_pct=delta_pct,
            direction="positive",
            headline="Local businesses thrive",
            person_example=(
                f"Small shops earn about \u20b9{daily_loss:,.0f} more per day. "
                f"Restaurant and hotel bookings increase."
            ),
            city_wide=f"About {jobs_count:,} new retail and hospitality jobs.",
            numbers={"daily_revenue_boost": round(daily_loss), "new_jobs": jobs_count},
        )


def _translate_informal(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate informal economy delta to plain language."""
    abs_delta = abs(delta_pct)
    daily_change = COST_PROXIES["street_vendor_daily_income"] * abs_delta / 100
    jobs = _jobs_in_sector(city_config, "informal")
    jobs_count = int(jobs * abs_delta / 100)

    if delta_pct < 0:
        return SectorImpact(
            sector="informal",
            sector_label="Street Vendors & Gig Workers",
            delta_pct=delta_pct,
            direction="negative",
            headline="Daily wage workers earn less",
            person_example=(
                f"Street vendors and gig workers see about \u20b9{abs(daily_change):,.0f}/day "
                f"drop in earnings."
            ),
            city_wide=f"Roughly {abs(jobs_count):,} informal workers affected.",
            numbers={
                "daily_income_loss": round(abs(daily_change)),
                "workers_affected": abs(jobs_count),
            },
        )
    else:
        return SectorImpact(
            sector="informal",
            sector_label="Street Vendors & Gig Workers",
            delta_pct=delta_pct,
            direction="positive",
            headline="Daily wage workers earn more",
            person_example=(
                f"Street vendors and gig workers see about \u20b9{daily_change:,.0f}/day "
                f"increase in earnings."
            ),
            city_wide=f"Roughly {jobs_count:,} informal workers benefit.",
            numbers={
                "daily_income_boost": round(daily_change),
                "workers_benefiting": jobs_count,
            },
        )


def _translate_public_admin(delta_pct: float, city_config: Any) -> SectorImpact:
    """Translate public administration delta to plain language."""
    abs_delta = abs(delta_pct)
    jobs = _jobs_in_sector(city_config, "public_admin")
    jobs_count = int(jobs * abs_delta / 100)
    wage_impact = COST_PROXIES["govt_contract_monthly"] * abs_delta / 100

    if delta_pct < 0:
        return SectorImpact(
            sector="public_admin",
            sector_label="Government & Public Services",
            delta_pct=delta_pct,
            direction="negative",
            headline="Government hiring slows",
            person_example=(
                f"About {abs(jobs_count):,} fewer government contract jobs "
                f"over the simulation period."
            ),
            city_wide=(
                f"Public services may face staffing pressure. "
                f"Contract workers lose about \u20b9{abs(wage_impact):,.0f}/month."
            ),
            numbers={
                "jobs_frozen": abs(jobs_count),
                "wage_loss_monthly": round(abs(wage_impact)),
            },
        )
    else:
        return SectorImpact(
            sector="public_admin",
            sector_label="Government & Public Services",
            delta_pct=delta_pct,
            direction="positive",
            headline="Government sector expands",
            person_example=(
                f"About {jobs_count:,} new government and contract jobs expected."
            ),
            city_wide=f"Public services expand; contract workers earn \u20b9{wage_impact:,.0f}/month more.",
            numbers={"new_jobs": jobs_count, "wage_boost_monthly": round(wage_impact)},
        )


# Map sector to its translator function
_SECTOR_TRANSLATORS = {
    "transport_logistics": _translate_transport,
    "it_ites": _translate_it,
    "manufacturing": _translate_manufacturing,
    "real_estate": _translate_real_estate,
    "trade_hospitality": _translate_trade,
    "informal": _translate_informal,
    "public_admin": _translate_public_admin,
}


def _generate_headline(
    sector_deltas: dict[str, float],
    city_config: Any,
    original_query: str,
) -> str:
    """Generate a headline that references the user's original question."""
    city_name = city_config.name

    # Find the dominant sector (largest absolute delta)
    active = {s: d for s, d in sector_deltas.items() if abs(d) > 0}
    if not active:
        return f"Simulation for {city_name} shows minimal change from current trends."

    dominant_sector = max(active, key=lambda s: abs(active[s]))
    delta = active[dominant_sector]

    # Try to connect to user's original words
    user_keyword = _find_user_keyword(original_query, dominant_sector)

    if user_keyword:
        if delta < -10:
            return (
                f"If {user_keyword} costs spike in {city_name}, "
                f"the biggest impact would be on {SECTOR_LABELS[dominant_sector].lower()} "
                f"\u2014 here is what that means for real people."
            )
        elif delta > 10:
            return (
                f"If {user_keyword} booms in {city_name}, "
                f"the biggest gains would be in {SECTOR_LABELS[dominant_sector].lower()} "
                f"\u2014 here is what that means for you."
            )

    # Generic headline
    if delta < -10:
        return (
            f"A {abs(delta):.0f}% drop in {SECTOR_LABELS[dominant_sector].lower()} "
            f"in {city_name} \u2014 here is how it affects daily life."
        )
    elif delta > 10:
        return (
            f"A {delta:.0f}% boost in {SECTOR_LABELS[dominant_sector].lower()} "
            f"in {city_name} \u2014 here is what changes."
        )
    return f"Simulation results for {city_name} show modest economic shifts."


def _generate_takeaways(
    metrics: AggregateMetrics,
    city_config: Any,
    sector_impacts: list[SectorImpact],
) -> list[str]:
    """Generate 3-5 plain-language takeaway bullets."""
    takeaways: list[str] = []
    city_name = city_config.name

    # GDP takeaway
    gdp_pct = metrics.gdpDelta * 100
    gdp_crores = city_config.baselines.get("gdp_estimate_crores", 100000)
    gdp_change_crores = abs(gdp_pct / 100 * gdp_crores)
    if abs(gdp_pct) > 0.5:
        direction = "grows" if gdp_pct > 0 else "shrinks"
        takeaways.append(
            f"{city_name}'s economy {direction} by about \u20b9{gdp_change_crores:,.0f} crores "
            f"({gdp_pct:+.1f}%)."
        )

    # Unemployment takeaway
    unemp = metrics.unemploymentRate * 100
    baseline_unemp = city_config.baselines.get("unemployment_rate", 0.04) * 100
    if abs(unemp - baseline_unemp) > 0.5:
        if unemp > baseline_unemp:
            takeaways.append(
                f"Unemployment rises from {baseline_unemp:.1f}% to {unemp:.1f}%, "
                f"meaning more people are looking for work."
            )
        else:
            takeaways.append(
                f"Unemployment drops from {baseline_unemp:.1f}% to {unemp:.1f}%, "
                f"meaning more jobs are available."
            )

    # Rent/housing takeaway
    housing = metrics.housingAffordability
    if housing < 0.9:
        takeaways.append(
            f"Housing becomes less affordable \u2014 rents go up and "
            f"families spend more of their income on housing."
        )
    elif housing > 1.1:
        takeaways.append(
            f"Housing becomes more affordable \u2014 rents drop "
            f"and families have more money for other expenses."
        )

    # Most affected sector
    if sector_impacts:
        worst = max(sector_impacts, key=lambda s: abs(s.delta_pct))
        if abs(worst.delta_pct) > 5:
            takeaways.append(
                f"The most affected area is {worst.sector_label.lower()} "
                f"({worst.delta_pct:+.0f}%), which impacts daily life for many residents."
            )

    # Congestion takeaway
    if metrics.transitCongestion > 0.7:
        takeaways.append(
            f"Traffic and public transport get more crowded, "
            f"increasing commute times for everyone."
        )
    elif metrics.transitCongestion < 0.3:
        takeaways.append(
            f"Traffic congestion eases, making commutes faster."
        )

    return takeaways[:5]


def _overall_verdict(metrics: AggregateMetrics) -> str:
    """Classify overall impact as a plain verdict."""
    gdp = metrics.gdpDelta * 100
    unemp = metrics.unemploymentRate * 100
    baseline_unemp = 4.0  # rough national average

    if gdp > 2 and unemp < baseline_unemp:
        return "Strong positive impact"
    if gdp > 0.5:
        return "Moderate positive impact"
    if gdp > -0.5:
        return "Minimal change"
    if gdp > -2:
        return "Moderate negative impact"
    return "Significant negative impact"


def _gdp_summary(metrics: AggregateMetrics, city_config: Any) -> str:
    """Plain-language GDP summary."""
    gdp_pct = metrics.gdpDelta * 100
    gdp_crores = city_config.baselines.get("gdp_estimate_crores", 100000)
    change_crores = abs(gdp_pct / 100 * gdp_crores)
    city_name = city_config.name

    if abs(gdp_pct) < 0.3:
        return f"{city_name}'s economy stays roughly the same."
    if gdp_pct > 0:
        return f"{city_name}'s economy grows by about \u20b9{change_crores:,.0f} crores ({gdp_pct:+.1f}%)."
    return f"{city_name}'s economy shrinks by about \u20b9{change_crores:,.0f} crores ({gdp_pct:+.1f}%)."


def _unemployment_summary(metrics: AggregateMetrics, city_config: Any) -> str:
    """Plain-language unemployment summary."""
    unemp = metrics.unemploymentRate * 100
    baseline = city_config.baselines.get("unemployment_rate", 0.04) * 100
    if abs(unemp - baseline) < 0.3:
        return f"Unemployment stays around {baseline:.1f}%."
    if unemp > baseline:
        return f"Unemployment rises from {baseline:.1f}% to {unemp:.1f}%."
    return f"Unemployment drops from {baseline:.1f}% to {unemp:.1f}%."


def translate_to_plain_language(
    sector_deltas: dict[str, float],
    metrics: AggregateMetrics,
    city_config: Any,
    original_query: str = "",
) -> TranslationResult:
    """Main entry point: translate simulation results to plain language."""
    sector_impacts: list[SectorImpact] = []

    for sector, delta in sector_deltas.items():
        if abs(delta) < 1.0:
            continue
        translator = _SECTOR_TRANSLATORS.get(sector)
        if translator:
            impact = translator(delta, city_config)
            sector_impacts.append(impact)

    # Sort by absolute delta (most impactful first)
    sector_impacts.sort(key=lambda s: abs(s.delta_pct), reverse=True)

    headline = _generate_headline(sector_deltas, city_config, original_query)
    takeaways = _generate_takeaways(metrics, city_config, sector_impacts)

    # Determine overall provenance
    has_news = any(s.origin == "real" for s in sector_impacts)
    origin = "real_time_context" if has_news else "estimated"
    confidence = 0.70 if has_news else 0.55
    confidence_label = "High" if confidence >= 0.7 else "Medium" if confidence >= 0.4 else "Low"

    return TranslationResult(
        headline=headline,
        sector_impacts=sector_impacts,
        takeaways=takeaways,
        gdp_summary=_gdp_summary(metrics, city_config),
        unemployment_summary=_unemployment_summary(metrics, city_config),
        overall_verdict=_overall_verdict(metrics),
        confidence=confidence,
        confidence_label=confidence_label,
        origin=origin,
        limitations=[
            "Estimates based on city baselines and news sentiment.",
            "Simulation coefficients are tuned, not from published research.",
            "Use for scenario exploration, not prediction.",
        ],
    )

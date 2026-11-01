"""AgentTools (the tools the /ws/agent loop calls) and AgentMemory. No network, no LLM."""
from __future__ import annotations

import types

import pytest

from engine.agent.memory import AgentMemory, MemoryEntry
from engine.agent.tools import AgentTools, ToolResult
from engine.config import CityConfig
from engine.models import ParsedScenario


def make_city(**overrides) -> CityConfig:
    values = dict(
        name="Testpur",
        state="Test State",
        population=2_500_000,
        city_type="tier2",
        baselines={"gdp_estimate_crores": 120_000, "unemployment_rate": 0.062},
        sector_weights={"it_ites": 0.3, "manufacturing": 0.5, "informal": 0.2, "public_admin": 0.0},
        special_zones=[{"name": "SEZ North"}, {"name": "Old Town"}],
    )
    values.update(overrides)
    return CityConfig(**values)


class StubRouter:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    async def route(self, text):
        self.calls.append(text)
        if self.error:
            raise self.error
        return self.result


class StubDb:
    def __init__(self, studies=None, error=None):
        self.studies, self.error, self.calls = studies or [], error, []

    async def search_case_studies(self, keywords, city=None, top_k=3):
        self.calls.append((keywords, city, top_k))
        if self.error:
            raise self.error
        return self.studies


def study(title, city="Pune", year=2019, description="x" * 300):
    return types.SimpleNamespace(
        title=title, city=city, year=year, description=description,
        model_dump=lambda: {"title": title, "city": city, "year": year},
    )


# ── ToolResult ───────────────────────────────────────────────────────────────


def test_tool_result_to_dict():
    assert ToolResult(success=False, error="boom").to_dict() == {
        "success": False, "data": None, "error": "boom", "summary": "",
    }


# ── parse_scenario ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_parse_scenario_summarises_active_sectors_only():
    parsed = ParsedScenario(
        city="pune",
        sector_deltas={"it_ites": 15.0, "manufacturing": 0.0, "real_estate": -5.0},
        policies_active=["metro_expansion"],
        horizon_months=36,
    )
    router = StubRouter(result=(parsed, 0.876))
    result = await AgentTools(intent_router=router).parse_scenario("IT grows in Pune")

    assert router.calls == ["IT grows in Pune"]
    assert result.success
    assert result.data["city"] == "pune"
    assert result.summary == (
        "City: pune, Sectors: IT/ITES +15%, Real Estate -5%, "
        "Policies: metro_expansion, Horizon: 36m, Confidence: 0.88"
    )


@pytest.mark.asyncio
async def test_parse_scenario_with_nothing_active_says_none():
    router = StubRouter(result=(ParsedScenario(city="pune"), 0.5))
    result = await AgentTools(intent_router=router).parse_scenario("hello")
    assert "Sectors: none" in result.summary
    assert "Policies: none" in result.summary


@pytest.mark.asyncio
async def test_parse_scenario_turns_router_errors_into_a_failed_result():
    router = StubRouter(error=RuntimeError("parser exploded"))
    result = await AgentTools(intent_router=router).parse_scenario("x")
    assert result == ToolResult(success=False, error="parser exploded")


# ── query_case_studies ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_query_case_studies_without_db():
    result = await AgentTools(intent_router=StubRouter()).query_case_studies(["metro"])
    assert not result.success
    assert result.error == "Database not available"


@pytest.mark.asyncio
async def test_query_case_studies_formats_precedents_and_truncates_descriptions():
    db = StubDb(studies=[study("Metro Phase 1"), study("Ring Road", city="Bengaluru", year=2012)])
    tools = AgentTools(intent_router=StubRouter(), db=db)
    result = await tools.query_case_studies(["metro", "transit"], city="pune", top_k=2)

    assert db.calls == [(["metro", "transit"], "pune", 2)]
    assert result.success
    assert result.data == [
        {"title": "Metro Phase 1", "city": "Pune", "year": 2019},
        {"title": "Ring Road", "city": "Bengaluru", "year": 2012},
    ]
    lines = result.summary.splitlines()
    assert lines[0] == "Relevant precedents:"
    assert lines[1] == "- Metro Phase 1 (Pune, 2019): " + "x" * 200
    assert lines[2].startswith("- Ring Road (Bengaluru, 2012): ")


@pytest.mark.asyncio
async def test_query_case_studies_with_no_hits_is_a_success():
    result = await AgentTools(intent_router=StubRouter(), db=StubDb()).query_case_studies(["x"])
    assert result.success
    assert result.data == []
    assert result.summary == "No matching case studies found."


@pytest.mark.asyncio
async def test_query_case_studies_reports_db_errors():
    db = StubDb(error=ConnectionError("db down"))
    result = await AgentTools(intent_router=StubRouter(), db=db).query_case_studies(["x"])
    assert not result.success
    assert result.error == "db down"


# ── get_city_profile ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_city_profile_from_injected_config():
    tools = AgentTools(intent_router=StubRouter(), city_configs={"testpur": make_city()})
    result = await tools.get_city_profile("testpur")

    assert result.success
    assert result.data == {
        "name": "Testpur",
        "state": "Test State",
        "type": "tier2",
        "population": 2_500_000,
        "gdp_crores": 120_000,
        "unemployment": 0.062,
        # Zero-weight sectors are left out.
        "sector_weights": {"IT/ITES": "30%", "Manufacturing": "50%", "Informal Economy": "20%"},
        "special_zones": ["SEZ North", "Old Town"],
    }
    assert result.summary == (
        "Testpur: tier2, pop 2,500,000, GDP 120,000cr, unemployment 6.2%. "
        "Key sectors: IT/ITES=30%, Manufacturing=50%, Informal Economy=20%"
    )


@pytest.mark.asyncio
async def test_get_city_profile_loads_and_caches_a_real_city():
    configs: dict[str, CityConfig] = {}
    tools = AgentTools(intent_router=StubRouter(), city_configs=configs)
    result = await tools.get_city_profile("bengaluru")
    assert result.success
    assert result.data["population"] == 13_000_000
    assert "bengaluru" in configs


@pytest.mark.asyncio
@pytest.mark.parametrize("city", ["atlantis", "../etc/passwd"])
async def test_get_city_profile_unknown_or_unsafe_city(city):
    result = await AgentTools(intent_router=StubRouter()).get_city_profile(city)
    assert not result.success
    assert result.error.startswith(f"City '{city}' not found")


@pytest.mark.asyncio
async def test_get_city_profile_handles_missing_optional_fields():
    cfg = make_city(baselines={}, sector_weights={}, special_zones=[])
    tools = AgentTools(intent_router=StubRouter(), city_configs={"bare": cfg})
    result = await tools.get_city_profile("bare")
    assert result.success
    assert result.data["gdp_crores"] == 0
    assert result.data["sector_weights"] == {}
    assert result.summary.endswith("Key sectors: ")


# ── list_cities / compare_sectors ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_cities_uses_display_names():
    result = await AgentTools(intent_router=StubRouter()).list_cities()
    assert result.success
    assert "Bengaluru" in result.data
    assert result.summary == "Available cities: " + ", ".join(result.data)


@pytest.mark.asyncio
async def test_compare_sectors_ranks_by_weighted_impact():
    tools = AgentTools(intent_router=StubRouter(), city_configs={"testpur": make_city()})
    result = await tools.compare_sectors(
        "testpur",
        {"it_ites": 20.0, "manufacturing": -10.0, "informal": 5.0, "real_estate": 0.0, "bogus": 99.0},
    )
    assert result.success
    assert [c["sector"] for c in result.data] == ["IT/ITES", "Manufacturing", "Informal Economy"]
    assert result.data[0] == {
        "sector": "IT/ITES", "delta_pct": 20.0, "weight_pct": 30.0, "weighted_impact": 6.0,
    }
    assert result.data[1]["weighted_impact"] == -5.0
    assert "  Manufacturing: -10% (weight 50.0%, weighted -5.00)" in result.summary.splitlines()


@pytest.mark.asyncio
async def test_compare_sectors_unknown_city_fails_cleanly():
    result = await AgentTools(intent_router=StubRouter()).compare_sectors("atlantis", {"it_ites": 5})
    assert not result.success
    assert result.error


def test_tool_descriptions_name_every_public_tool():
    text = AgentTools(intent_router=StubRouter()).get_tool_descriptions()
    for name in ("parse_scenario", "query_case_studies", "get_city_profile", "list_cities", "compare_sectors"):
        assert f"{name}(" in text
        assert callable(getattr(AgentTools, name))


# ── AgentMemory ──────────────────────────────────────────────────────────────


def test_memory_keeps_the_last_two_entries_per_turn_cap():
    memory = AgentMemory(max_turns=2)
    for i in range(7):
        memory.add_user(f"u{i}")
    assert [e.content for e in memory.get_history()] == ["u3", "u4", "u5", "u6"]
    assert memory.turn_count == 4


def test_memory_history_can_hide_tool_results():
    memory = AgentMemory()
    memory.add_user("hi")
    memory.add_tool("list_cities", {}, "Pune, Mumbai")
    memory.add_assistant("done", metadata={"steps": 1})
    assert [e.role for e in memory.get_history()] == ["user", "tool", "assistant"]
    assert [e.role for e in memory.get_history(include_tool_results=False)] == ["user", "assistant"]
    assert memory.get_history()[2].metadata == {"steps": 1}
    # get_history returns a copy.
    memory.get_history().clear()
    assert len(memory.get_history()) == 3


def test_memory_formatted_history_keeps_newest_within_budget():
    memory = AgentMemory()
    memory.add_user("a" * 30)
    memory.add_tool("get_city_profile", {"city": "pune"}, "b" * 30)
    memory.add_assistant("c" * 30)
    full = memory.get_formatted_history()
    assert full.split("\n\n") == [
        "User: " + "a" * 30,
        "Tool (get_city_profile): " + "b" * 30,
        "Assistant: " + "c" * 30,
    ]
    # 20 tokens = 80 chars: only the newest entries that fit, oldest dropped first.
    trimmed = memory.get_formatted_history(max_tokens=20)
    assert trimmed == "Assistant: " + "c" * 30


def test_memory_to_dict_and_clear():
    memory = AgentMemory()
    memory.add(MemoryEntry(role="tool", content="r", tool_name="t", tool_args={"k": 1}))
    assert memory.to_dict() == [{"role": "tool", "content": "r", "tool_name": "t", "tool_args": {"k": 1}}]
    memory.clear()
    assert memory.to_dict() == []
    assert memory.turn_count == 0

"""UrbanAgent ReAct loop, AgentMemory and AgentTools, driven by a scripted LLM (no network)."""
from __future__ import annotations

import asyncio
import json

import pytest

from engine.agent import AgentMemory, AgentTools, ToolResult, UrbanAgent
from engine.agent.agent import AgentState


def scripted(*replies):
    """LLM stub returning the given replies in order (dicts are JSON-encoded) and recording prompts."""
    queue = [r if isinstance(r, str) else json.dumps(r) for r in replies]
    prompts: list[str] = []

    async def llm(prompt: str) -> str:
        prompts.append(prompt)
        if not queue:
            return json.dumps({"type": "final", "content": "fallback final"})
        return queue.pop(0)

    llm.prompts = prompts  # type: ignore[attr-defined]
    return llm


async def collect(agent: UrbanAgent, message: str) -> list[dict]:
    return [e async for e in agent.run(message)]


class StubTools(AgentTools):
    def __init__(self):
        super().__init__()
        self.calls: list[tuple[str, dict]] = []

    async def get_city_profile(self, city: str) -> ToolResult:
        self.calls.append(("get_city_profile", {"city": city}))
        return ToolResult(success=True, data={"name": city}, summary=f"{city}: profile ok")

    async def list_cities(self) -> ToolResult:
        self.calls.append(("list_cities", {}))
        return ToolResult(success=False, error="cities offline")


# ── response parsing ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        '{"type": "final", "content": "ok"}',
        '```json\n{"type": "final", "content": "ok"}\n```',
        '```\njson\n{"type": "final", "content": "ok"}\n```',
        'Sure! Here you go: {"type": "final", "content": "ok"} hope that helps',
    ],
)
def test_parse_response_accepts_fenced_and_wrapped_json(raw):
    assert UrbanAgent()._parse_response(raw) == {"type": "final", "content": "ok"}


def test_parse_response_turns_garbage_into_error():
    parsed = UrbanAgent()._parse_response("I cannot answer in JSON today")
    assert parsed["type"] == "error"


# ── run loop ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_think_then_final_streams_events_and_summary():
    llm = scripted({"type": "think", "content": "plan"}, {"type": "final", "content": "answer"})
    agent = UrbanAgent(llm_fn=llm, tools=StubTools())
    events = await collect(agent, "Help Pune grow IT jobs")

    assert [e["type"] for e in events] == ["agent_think", "agent_result"]
    assert events[1]["content"] == "answer"
    assert events[1]["summary"] == {"steps_taken": 2, "tools_used": [], "turns": 1}
    assert agent.state is AgentState.DONE
    # The thought is fed back into the next prompt.
    assert "[Assistant thinking: plan]" in llm.prompts[1]


@pytest.mark.asyncio
async def test_tool_call_result_is_recorded_and_fed_back():
    tools = StubTools()
    llm = scripted(
        {"type": "tool_call", "tool": "get_city_profile", "args": {"city": "pune"}},
        {"type": "final", "content": "done"},
    )
    agent = UrbanAgent(llm_fn=llm, tools=tools)
    events = await collect(agent, "Profile Pune please")

    assert events[0] == {"type": "agent_action", "tool": "get_city_profile", "args": {"city": "pune"}}
    assert tools.calls == [("get_city_profile", {"city": "pune"})]
    assert "[Tool 'get_city_profile' result: pune: profile ok]" in llm.prompts[1]
    assert events[-1]["summary"]["tools_used"] == ["get_city_profile"]
    tool_entries = [e for e in agent.memory.get_history() if e.role == "tool"]
    assert tool_entries[0].content == "pune: profile ok"


@pytest.mark.asyncio
async def test_failed_and_unknown_tools_do_not_end_the_run():
    llm = scripted(
        {"type": "tool_call", "tool": "list_cities", "args": {}},
        {"type": "tool_call", "tool": "launch_rocket", "args": {}},
        {"type": "tool_call", "tool": "get_city_profile", "args": {"town": "pune"}},
        {"type": "final", "content": "recovered"},
    )
    agent = UrbanAgent(llm_fn=llm, tools=StubTools())
    events = await collect(agent, "Try some tools")

    assert events[-1]["type"] == "agent_result"
    assert "[Tool 'list_cities' failed: cities offline]" in llm.prompts[1]
    assert "[Tool 'launch_rocket' failed: Unknown tool: launch_rocket]" in llm.prompts[2]
    # Wrong kwarg name raises TypeError inside the tool map; it becomes a failed result.
    assert "[Tool 'get_city_profile' failed:" in llm.prompts[3]


@pytest.mark.asyncio
async def test_ask_waits_for_reply_and_records_it():
    llm = scripted(
        {"type": "ask", "question": "Which city?", "options": ["Pune", "Surat"]},
        {"type": "final", "content": "Surat it is"},
    )
    agent = UrbanAgent(llm_fn=llm, tools=StubTools())
    events: list[dict] = []
    async for event in agent.run("Grow a city"):
        events.append(event)
        if event["type"] == "__wait_for_reply":
            assert agent.state is AgentState.AWAITING_INPUT
            # Reply arrives later, as it would from the socket.
            asyncio.get_running_loop().call_soon(agent.provide_reply, "Surat")

    assert [e["type"] for e in events] == ["agent_ask", "__wait_for_reply", "agent_result"]
    assert events[0]["options"] == ["Pune", "Surat"]
    assert "[User replied: Surat]" in llm.prompts[1]
    assert agent.memory.turn_count == 2


@pytest.mark.asyncio
async def test_error_type_and_unparseable_output_end_with_agent_error():
    agent = UrbanAgent(llm_fn=scripted({"type": "error", "content": "cannot help"}))
    events = await collect(agent, "anything")
    assert events == [{"type": "agent_error", "content": "cannot help"}]
    assert agent.state is AgentState.ERROR

    agent = UrbanAgent(llm_fn=scripted("not json at all"))
    events = await collect(agent, "anything")
    assert events[0]["type"] == "agent_error"


@pytest.mark.asyncio
async def test_unknown_type_is_corrected_and_step_limit_returns_partial_result():
    llm = scripted(*[{"type": "dance"}] * 5)
    agent = UrbanAgent(llm_fn=llm, max_steps=3)
    events = await collect(agent, "loop forever")

    assert len(llm.prompts) == 3
    assert "unknown type" in llm.prompts[1]
    assert events == [{
        "type": "agent_result",
        "content": "I reached the step limit but here's my analysis so far.",
        "summary": {"steps_taken": 3, "tools_used": [], "turns": 1},
    }]


@pytest.mark.asyncio
async def test_without_llm_the_fallback_calls_list_cities():
    tools = StubTools()
    agent = UrbanAgent(llm_fn=None, tools=tools, max_steps=1)
    events = await collect(agent, "no model configured")
    assert events[0] == {"type": "agent_action", "tool": "list_cities", "args": {}}
    assert ("list_cities", {}) in tools.calls


def test_first_prompt_contains_system_prompt_tools_and_message():
    agent = UrbanAgent(tools=AgentTools())
    agent.memory.add_user("Help Surat")
    prompt = agent._build_context("Help Surat")
    assert "MetroPulse Agent" in prompt
    assert "AVAILABLE TOOLS" in prompt
    assert "User message: Help Surat" in prompt


def test_reset_clears_state():
    agent = UrbanAgent()
    agent.memory.add_user("x")
    agent._step_count = 4
    agent.reset()
    assert agent.state is AgentState.IDLE
    assert agent.memory.turn_count == 0
    assert agent._step_count == 0


# ── memory ─────────────────────────────────────────────────────────────────


def test_memory_keeps_only_the_newest_entries():
    mem = AgentMemory(max_turns=2)
    for i in range(7):
        mem.add_user(f"u{i}")
    assert [e.content for e in mem.get_history()] == ["u3", "u4", "u5", "u6"]
    assert mem.turn_count == 4


def test_memory_formatting_respects_budget_and_filters_tools():
    mem = AgentMemory()
    mem.add_user("a" * 10)
    mem.add_tool("list_cities", {}, "b" * 10)
    mem.add_assistant("c" * 10)

    full = mem.get_formatted_history()
    assert full.splitlines()[0].startswith("User: ")
    assert "Tool (list_cities): " + "b" * 10 in full

    # Budget of 6 tokens = 24 chars: only the newest entry (21 chars) fits.
    assert mem.get_formatted_history(max_tokens=6) == "Assistant: " + "c" * 10
    assert [e.role for e in mem.get_history(include_tool_results=False)] == ["user", "assistant"]
    assert mem.to_dict()[1]["tool_name"] == "list_cities"
    mem.clear()
    assert mem.get_history() == []


# ── tools ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_sectors_weights_and_sorts_by_impact():
    result = await AgentTools().compare_sectors(
        "pune", {"it_ites": 10, "manufacturing": -40, "public_admin": 0}
    )
    assert result.success
    assert [c["sector"] for c in result.data] == ["Manufacturing", "IT/ITES"]
    assert result.data[0] == {
        "sector": "Manufacturing", "delta_pct": -40, "weight_pct": 20.0, "weighted_impact": -8.0,
    }
    assert "IT/ITES: +10%" in result.summary


@pytest.mark.asyncio
async def test_city_profile_is_cached_and_unknown_city_fails_cleanly():
    tools = AgentTools()
    ok = await tools.get_city_profile("pune")
    assert ok.success and ok.data["name"] == "Pune"
    assert "IT/ITES=30%" in ok.summary
    assert "pune" in tools._city_configs

    missing = await tools.get_city_profile("atlantis")
    assert not missing.success
    assert "atlantis" in missing.error


@pytest.mark.asyncio
async def test_list_cities_and_case_studies_without_db():
    tools = AgentTools()
    cities = await tools.list_cities()
    assert cities.success and "Pune" in cities.data and len(cities.data) == 30

    no_db = await tools.query_case_studies(["metro"])
    assert no_db == ToolResult(success=False, error="Database not available")


@pytest.mark.asyncio
async def test_query_case_studies_summarises_db_results():
    class Study:
        def __init__(self, title):
            self.title, self.city, self.year, self.description = title, "Pune", 2015, "x" * 300

        def model_dump(self):
            return {"title": self.title}

    class Db:
        def __init__(self, rows):
            self.rows = rows
            self.args = None

        async def search_case_studies(self, keywords, city="", top_k=3):
            self.args = (keywords, city, top_k)
            return self.rows

    db = Db([Study("Hinjewadi IT park")])
    result = await AgentTools(db=db).query_case_studies(["it"], city="pune", top_k=1)
    assert db.args == (["it"], "pune", 1)
    assert result.data == [{"title": "Hinjewadi IT park"}]
    assert result.summary.startswith("Relevant precedents:\n- Hinjewadi IT park (Pune, 2015): ")
    assert result.summary.endswith("x" * 200)

    empty = await AgentTools(db=Db([])).query_case_studies(["none"])
    assert empty.success and empty.data == [] and "No matching" in empty.summary


@pytest.mark.asyncio
async def test_parse_scenario_reports_active_sectors():
    result = await AgentTools().parse_scenario("Increase IT jobs in Pune by 20% over 24 months")
    assert result.success
    assert result.summary.startswith("City: ")
    assert "Confidence:" in result.summary
    assert isinstance(result.data, dict) and "sector_deltas" in result.data

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from typing import Any, AsyncIterator, Callable, Coroutine

from engine.agent.memory import AgentMemory
from engine.agent.tools import AgentTools, ToolResult
from engine.agent.prompts import REACT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    AWAITING_INPUT = "awaiting_input"
    EXECUTING = "executing"
    DONE = "done"
    ERROR = "error"


class UrbanAgent:
    def __init__(
        self,
        llm_fn: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        tools: AgentTools | None = None,
        max_steps: int = 15,
    ) -> None:
        self._llm_fn = llm_fn
        self._tools = tools or AgentTools()
        self._memory = AgentMemory()
        self._state = AgentState.IDLE
        self._max_steps = max_steps
        self._step_count = 0
        self._last_error: str | None = None
        self._reply_event: asyncio.Event | None = None
        self._pending_reply: str | None = None

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def memory(self) -> AgentMemory:
        return self._memory

    def provide_reply(self, text: str) -> None:
        self._pending_reply = text
        if self._reply_event is not None:
            self._reply_event.set()

    async def run(
        self,
        user_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        self._memory.add_user(user_message)
        self._step_count = 0
        self._state = AgentState.THINKING

        full_context = self._build_context(user_message)

        while self._step_count < self._max_steps:
            self._step_count += 1
            self._state = AgentState.THINKING

            response_text = await self._call_llm(full_context)

            parsed = self._parse_response(response_text)

            if parsed["type"] == "think":
                logger.info("Agent think (%d): %s", self._step_count, parsed["content"][:200])
                yield {"type": "agent_think", "content": parsed["content"]}
                full_context += f"\n\n[Assistant thinking: {parsed['content']}]\n\nContinue with your next JSON action."
                continue

            elif parsed["type"] == "tool_call":
                self._state = AgentState.EXECUTING
                tool_name = parsed.get("tool", "")
                args = parsed.get("args", {})

                logger.info("Agent tool (%d): %s %s", self._step_count, tool_name, args)
                yield {"type": "agent_action", "tool": tool_name, "args": args}

                result = await self._execute_tool(tool_name, args)

                self._memory.add_tool(tool_name, args, result.summary if result.success else result.error or "")
                self._state = AgentState.THINKING

                if result.success:
                    full_context += (
                        f"\n\n[Tool '{tool_name}' result: {result.summary}]"
                        f"\n\nBased on this result, decide your next JSON action."
                    )
                else:
                    full_context += (
                        f"\n\n[Tool '{tool_name}' failed: {result.error}]"
                        f"\n\nTry a different approach or ask the user for clarification."
                    )
                continue

            elif parsed["type"] == "ask":
                self._state = AgentState.AWAITING_INPUT
                question = parsed.get("question", "Could you clarify?")
                options = parsed.get("options", [])

                yield {"type": "agent_ask", "question": question, "options": options}

                self._reply_event = asyncio.Event()
                yield {"type": "__wait_for_reply"}
                await self._reply_event.wait()
                self._reply_event = None

                user_reply = self._pending_reply or ""
                self._pending_reply = None
                self._memory.add_user(user_reply)
                self._state = AgentState.THINKING
                full_context += f"\n\n[User replied: {user_reply}]\n\nContinue based on their response."

            elif parsed["type"] == "final":
                self._state = AgentState.DONE
                yield {
                    "type": "agent_result",
                    "content": parsed.get("content", ""),
                    "summary": self._build_summary(),
                }
                return

            elif parsed["type"] == "error":
                self._state = AgentState.ERROR
                self._last_error = parsed.get("content", "Unknown error")
                yield {"type": "agent_error", "content": self._last_error}
                return

            else:
                logger.warning("Agent: unknown type %s", parsed.get("type"))
                full_context += (
                    "\n\n[Your response had an unknown type. "
                    "Respond with valid JSON: think, tool_call, ask, final, or error.]"
                )

        self._state = AgentState.DONE
        yield {
            "type": "agent_result",
            "content": "I reached the step limit but here's my analysis so far.",
            "summary": self._build_summary(),
        }

    def _build_context(self, user_message: str) -> str:
        history = self._memory.get_formatted_history(max_tokens=2000)
        tool_descriptions = self._tools.get_tool_descriptions()

        if self._memory.turn_count <= 1:
            context = (
                f"{REACT_SYSTEM_PROMPT}\n\n"
                f"{tool_descriptions}\n\n"
                f"Previous conversation:\n{history}\n\n"
                f"User message: {user_message}\n\n"
                f"Now respond with your first JSON action (think, tool_call, or ask):"
            )
        else:
            context = (
                f"{REACT_SYSTEM_PROMPT}\n\n"
                f"{tool_descriptions}\n\n"
                f"Previous conversation:\n{history}\n\n"
                f"Current step ({self._step_count + 1}/{self._max_steps}). "
                f"Respond with your next JSON action:"
            )
        return context

    async def _call_llm(self, prompt: str) -> str:
        if self._llm_fn is not None:
            return await self._llm_fn(prompt)
        logger.warning("No LLM function, using fallback")
        return json.dumps({"type": "tool_call", "tool": "list_cities", "args": {}})

    def _parse_response(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if "```json" in cleaned:
            start = cleaned.find("```json") + 7
            end = cleaned.find("```", start)
            if end > start:
                cleaned = cleaned[start:end].strip()
        elif "```" in cleaned:
            start = cleaned.find("```") + 3
            end = cleaned.find("```", start)
            if end > start:
                cleaned = cleaned[start:end].strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()

        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            cleaned = cleaned[brace_start: brace_end + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse: %s", text[:200])
            return {"type": "error", "content": "I had trouble structuring my response. Let me try again."}

    async def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        tool_map = {
            "parse_scenario": lambda: self._tools.parse_scenario(**args),
            "query_case_studies": lambda: self._tools.query_case_studies(**args),
            "get_city_profile": lambda: self._tools.get_city_profile(**args),
            "list_cities": lambda: self._tools.list_cities(),
            "compare_sectors": lambda: self._tools.compare_sectors(**args),
        }
        handler = tool_map.get(tool_name)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        try:
            return await handler()
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return ToolResult(success=False, error=str(e))

    def _build_summary(self) -> dict[str, Any]:
        return {
            "steps_taken": self._step_count,
            "tools_used": list({e.tool_name for e in self._memory._entries if e.tool_name}),
            "turns": self._memory.turn_count,
        }

    def reset(self) -> None:
        self._memory.clear()
        self._state = AgentState.IDLE
        self._step_count = 0
        self._last_error = None
        self._pending_reply = None
        self._reply_event = None

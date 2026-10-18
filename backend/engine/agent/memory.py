from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentMemory:
    def __init__(self, max_turns: int = 20) -> None:
        self._entries: list[MemoryEntry] = []
        self._max_turns = max_turns

    def add(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_turns * 2:
            self._entries = self._entries[-(self._max_turns * 2):]

    def add_user(self, content: str) -> None:
        self.add(MemoryEntry(role="user", content=content))

    def add_assistant(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        self.add(MemoryEntry(role="assistant", content=content, metadata=metadata or {}))

    def add_tool(self, tool_name: str, args: dict[str, Any], result: str) -> None:
        self.add(MemoryEntry(role="tool", content=result, tool_name=tool_name, tool_args=args))

    def get_history(self, include_tool_results: bool = True) -> list[MemoryEntry]:
        if include_tool_results:
            return list(self._entries)
        return [e for e in self._entries if e.role != "tool"]

    def get_formatted_history(self, max_tokens: int = 4000) -> str:
        lines: list[str] = []
        char_budget = max_tokens * 4
        used = 0
        for entry in reversed(self._entries):
            prefix = {"user": "User", "assistant": "Assistant", "tool": f"Tool ({entry.tool_name})"}.get(entry.role, entry.role)
            text = f"{prefix}: {entry.content}"
            if used + len(text) > char_budget:
                break
            lines.insert(0, text)
            used += len(text)
        return "\n\n".join(lines)

    def clear(self) -> None:
        self._entries.clear()

    @property
    def turn_count(self) -> int:
        return sum(1 for e in self._entries if e.role == "user")

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "role": e.role,
                "content": e.content,
                "tool_name": e.tool_name,
                "tool_args": e.tool_args,
            }
            for e in self._entries
        ]

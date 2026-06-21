from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw_arguments: str = "{}"


@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    assistant_message: dict = field(default_factory=dict)


class LLMClient(ABC):
    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict],
             tool_choice: str = "auto") -> LLMResponse:
        ...

    def complete(self, messages: list[dict]) -> str:
        raise NotImplementedError


def build_assistant_message(content: Optional[str], tool_calls: list[ToolCall]) -> dict:
    msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
    if tool_calls:
        msg["tool_calls"] = [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.name, "arguments": tc.raw_arguments}}
            for tc in tool_calls
        ]
    return msg


def tool_result_message(tool_call_id: str, result: Any) -> dict:
    return {"role": "tool", "tool_call_id": tool_call_id,
            "content": json.dumps(result, ensure_ascii=False, default=str)}

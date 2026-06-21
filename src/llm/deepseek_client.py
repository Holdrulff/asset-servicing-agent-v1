from __future__ import annotations

import json
import os
import time
from typing import Any

from openai import (  # type: ignore
    APIConnectionError,
    APIError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from .base import LLMClient, LLMResponse, ToolCall, build_assistant_message

TRANSIENT_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError)


def _tool_arguments(raw_arguments: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        model,
        base_url,
        api_key_env,
        temperature=0.0,
        max_attempts=4,
        backoff_base_s=2.0,
        request_timeout_s=60.0,
    ):
        super().__init__(model, temperature)
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Variável {api_key_env} não definida. Crie .env a partir de .env.example "
                f"ou use --provider replay para rodar offline."
            )
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=request_timeout_s)
        self._max_attempts = max_attempts
        self._backoff = backoff_base_s

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(self._backoff * (2 ** attempt))

    def _create(self, **kwargs):
        for attempt in range(self._max_attempts):
            try:
                return self._client.chat.completions.create(**kwargs)
            except TRANSIENT_ERRORS:
                if attempt == self._max_attempts - 1:
                    raise
                self._sleep_before_retry(attempt)
            except APIError as exc:
                status = getattr(exc, "status_code", None)
                if (status is not None and status < 500) or attempt == self._max_attempts - 1:
                    raise
                self._sleep_before_retry(attempt)
        raise RuntimeError("falha inesperada ao chamar o provider LLM")

    def chat(self, messages, tools, tool_choice="auto") -> LLMResponse:
        response = self._create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=self.temperature,
        )
        message = response.choices[0].message
        tool_calls = []
        for tool_call in message.tool_calls or []:
            raw_arguments = tool_call.function.arguments or "{}"
            tool_calls.append(
                ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=_tool_arguments(raw_arguments),
                    raw_arguments=raw_arguments,
                )
            )

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
            assistant_message=build_assistant_message(message.content, tool_calls),
        )

    def complete(self, messages) -> str:
        response = self._create(model=self.model, messages=messages, temperature=self.temperature)
        return response.choices[0].message.content or ""

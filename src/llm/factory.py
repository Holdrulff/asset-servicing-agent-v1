from __future__ import annotations

from .base import LLMClient
from .deepseek_client import OpenAICompatibleClient
from .replay_client import ReplayClient


def make_client(provider: str, config: dict) -> LLMClient:
    pconf = config.get("providers", {}).get(provider)
    if pconf is None:
        raise ValueError(f"provider desconhecido: {provider}")
    temperature = config.get("temperature", 0.0)

    if provider == "replay":
        return ReplayClient(model=pconf.get("model", "replay-fixtures"), temperature=temperature)

    retry = config.get("retry", {})
    return OpenAICompatibleClient(
        model=pconf["model"],
        base_url=pconf["base_url"],
        api_key_env=pconf["api_key_env"],
        temperature=temperature,
        max_attempts=retry.get("max_attempts", 4),
        backoff_base_s=retry.get("backoff_base_s", 2.0),
        request_timeout_s=config.get("request_timeout_s", 60.0),
    )

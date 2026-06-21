from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from .prompts import CRITIC_SYSTEM

CRITIC_CONTEXT_CHARS = 6000


def _default_verdict() -> dict[str, Any]:
    return {"veredito_geral": "ok", "rebaixar_confianca": False, "campos": [], "parse_ok": False}


def _json_object_slice(raw: str) -> str | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return None
    return raw[start:end + 1]


def _parse(raw: str) -> dict:
    json_text = _json_object_slice((raw or "").strip())
    if not json_text:
        return _default_verdict()

    try:
        parsed = json.loads(json_text)
    except JSONDecodeError:
        return _default_verdict()

    if not isinstance(parsed, dict):
        return _default_verdict()

    verdict = _default_verdict() | parsed
    if not isinstance(verdict.get("campos"), list):
        verdict["campos"] = []
    verdict["rebaixar_confianca"] = bool(verdict.get("rebaixar_confianca"))
    verdict["parse_ok"] = True
    return verdict


def run_critic(llm, document_text: str, submission: dict, tracer=None) -> dict:
    payload = {
        "texto_do_documento": (document_text or "")[:CRITIC_CONTEXT_CHARS],
        "registro_extraido": submission,
    }
    messages = [
        {"role": "system", "content": CRITIC_SYSTEM},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
    ]
    try:
        verdict = _parse(llm.complete(messages))
        verdict["ran"] = True
    except Exception as exc:
        verdict = _default_verdict() | {"ran": False, "reason": str(exc)}
    if tracer:
        tracer.critic(verdict)
    return verdict

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


class Tracer:
    def __init__(self, document_id: str, trace_path: Path | None = None):
        self.document_id = document_id
        self.trace_path = trace_path
        self.events: list[dict] = []
        self._t0 = time.perf_counter()
        if trace_path:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text("", encoding="utf-8")

    def log(self, event_type: str, **payload) -> None:
        evt = {
            "ts": now_iso(),
            "elapsed_s": round(time.perf_counter() - self._t0, 3),
            "document_id": self.document_id,
            "type": event_type,
            **{k: _safe(v) for k, v in payload.items()},
        }
        self.events.append(evt)
        if self.trace_path:
            with self.trace_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(evt, ensure_ascii=False) + "\n")

    def llm_request(self, step, n_messages, tools):
        self.log("llm_request", step=step, n_messages=n_messages, tools=tools)

    def llm_response(self, step, content, tool_calls, usage):
        self.log("llm_response", step=step, content=content, tool_calls=tool_calls, usage=usage)

    def tool_call(self, step, name, args):
        self.log("tool_call", step=step, name=name, args=args)

    def tool_result(self, step, name, result):
        self.log("tool_result", step=step, name=name, result=result)

    def reasoning(self, step, thought, phase=None):
        self.log("reasoning", step=step, thought=thought, phase=phase)

    def guardrail(self, decision):
        self.log("guardrail", decision=decision)

    def critic(self, verdict):
        self.log("critic", verdict=verdict)

    def self_consistency(self, field, runs, agreement):
        self.log("self_consistency", field=field, runs=runs, agreement=agreement)

    def final(self, status, review_required, reasons):
        self.log("final", status=status, review_required=review_required, reasons=reasons)

    def duration(self) -> float:
        return round(time.perf_counter() - self._t0, 3)

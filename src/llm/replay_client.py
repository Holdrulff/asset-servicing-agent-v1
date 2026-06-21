from __future__ import annotations

import json
import re

from .base import LLMClient, LLMResponse, ToolCall, build_assistant_message
from .replay_data import FIXTURES

_DOC_RE = re.compile(r"DOCUMENT_ID:\s*([0-9A-Za-z_]+)")


def _tc(idx, name, args) -> ToolCall:
    raw = json.dumps(args, ensure_ascii=False)
    return ToolCall(id=f"replay_{name}_{idx}", name=name, arguments=args, raw_arguments=raw)


class ReplayClient(LLMClient):
    def __init__(self, model="replay-fixtures", temperature=0.0):
        super().__init__(model, temperature)

    def _doc_id(self, messages):
        for m in messages:
            content = m.get("content") or ""
            if isinstance(content, str):
                hit = _DOC_RE.search(content)
                if hit:
                    return hit.group(1)
        raise RuntimeError("ReplayClient: DOCUMENT_ID não encontrado nas mensagens")

    def _turns(self, fx):
        sub = fx["submission"]
        path = fx["path"]
        turns = [[_tc(0, "read_document", {"pdf_path": path})]]
        if fx["scanned"]:
            turns.append([_tc(1, "run_ocr", {"pdf_path": path})])

        dates = {k: v.get("value") for k, v in sub["dates"].items()}
        vor = sub["value_or_ratio"]
        validations = [
            _tc(2, "validate_isin", {"isin": sub["isin"]["value"]}),
            _tc(3, "lookup_golden_record", {
                "isin": sub["isin"]["value"], "ticker": sub["ticker"]["value"],
                "cnpj": sub["cnpj"]["value"], "issuer": sub["issuer"]["value"]}),
            _tc(4, "check_date_coherence", {"dates": dates}),
            _tc(5, "check_value_coherence", {
                "kind": vor["kind"], "gross_value": vor.get("gross_value"),
                "net_value": vor.get("net_value"), "irrf_rate": vor.get("irrf_rate")}),
        ]
        turns.append(validations)
        turns.append([_tc(6, "submit_record", sub)])
        return turns

    def complete(self, messages) -> str:
        return '{"campos": [], "veredito_geral": "ok", "rebaixar_confianca": false}'

    def chat(self, messages, tools, tool_choice="auto") -> LLMResponse:
        fx = FIXTURES[self._doc_id(messages)]
        turns = self._turns(fx)
        idx = min(sum(1 for m in messages if m.get("role") == "assistant"), len(turns) - 1)
        calls = turns[idx]
        content = f"[replay turn {idx}] {fx['submission'].get('overall_rationale', '')}"
        return LLMResponse(content=content, tool_calls=calls, usage={"total_tokens": 0},
                           assistant_message=build_assistant_message(content, calls))

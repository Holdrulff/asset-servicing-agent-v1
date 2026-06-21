"""Testes do AGENT LOOP com LLMClient mockado (sem API)."""
from src.agent.loop import run_agent, REQUIRED_BEFORE_SUBMIT, ToolExecutor
from src.llm.base import LLMClient, LLMResponse, ToolCall, build_assistant_message
from src.llm.replay_client import ReplayClient
from src.observability import Tracer

CONFIG = {
    "golden_path": "data/golden_records/golden records.csv",
    "max_steps": 12, "ocr": {"lang": "por"},
    "providers": {"replay": {"model": "replay-fixtures"}}, "provider": "replay",
}


def test_replay_terminates_after_validations():
    llm = ReplayClient()
    res = run_agent("01_energetica_vale_tiete_dividendo", "data/documents/01_energetica_vale_tiete_dividendo.pdf",
                    llm, CONFIG, Tracer("01_energetica_vale_tiete_dividendo", None))
    assert res["terminated"] is True
    assert res["submission"] is not None
    assert res["document_text"].strip()
    # as validações obrigatórias foram chamadas antes do submit
    assert REQUIRED_BEFORE_SUBMIT.issubset(set(res["validations_called"]))


class _SubmitFirstClient(LLMClient):
    """Cliente malicioso: tenta submeter ANTES de validar. O loop deve bloquear."""
    def __init__(self):
        super().__init__("fake", 0.0)

    def chat(self, messages, tools, tool_choice="auto") -> LLMResponse:
        tc = ToolCall(id="x", name="submit_record",
                      arguments={"issuer": {"value": "X", "confidence_score": 0.9}},
                      raw_arguments="{}")
        return LLMResponse(content=None, tool_calls=[tc], usage={},
                           assistant_message=build_assistant_message(None, [tc]))


def test_submit_blocked_without_validations_escalates():
    res = run_agent("01_energetica_vale_tiete_dividendo", "data/documents/01_energetica_vale_tiete_dividendo.pdf",
                    _SubmitFirstClient(), CONFIG, Tracer("01_energetica_vale_tiete_dividendo", None))
    # nunca validou => submit sempre bloqueado => estoura orçamento => terminated False
    assert res["terminated"] is False
    assert res["submission"] is None


def test_tool_executor_reports_invalid_page_argument_without_crashing():
    tracer = Tracer("x", None)
    executor = ToolExecutor(CONFIG["golden_path"], "por", tracer)

    result = executor.run(2, "read_page", {"pdf_path": "missing.pdf", "page_number": "abc"})

    assert "page_number inválido" in result["error"]
    assert tracer.events[0]["type"] == "tool_call"
    assert tracer.events[0]["step"] == 2


def test_tool_executor_blocks_path_outside_allowed_root():
    from pathlib import Path

    executor = ToolExecutor(CONFIG["golden_path"], "por", Tracer("x", None),
                            allowed_root=Path("data/documents").resolve())

    result = executor.run(1, "read_document", {"pdf_path": "README.md"})

    assert "fora do diretório permitido" in result["error"]

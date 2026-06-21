from copy import deepcopy

from src.agent.harness import (
    _critic_document_text, _empty_submission, _recompute_validation, process_document,
)
from src.llm.base import LLMClient
from src.llm.replay_data import FIXTURES
from src.observability import Tracer
from src.schema import AgentSubmission

GOLDEN_PATH = "data/golden_records/golden records.csv"

_CONFIG = {
    "golden_path": GOLDEN_PATH, "max_steps": 12, "ocr": {"lang": "por"},
    "providers": {"replay": {"model": "replay-fixtures"}}, "provider": "replay",
    "prompt_version": "test", "thresholds": {"low_confidence_score": 0.6},
    "self_consistency": {"enabled": False}, "critic": {"enabled": False},
}


class _BoomClient(LLMClient):
    def __init__(self):
        super().__init__("boom", 0.0)

    def chat(self, messages, tools, tool_choice="auto"):
        raise RuntimeError("falha simulada do provider")


def test_empty_submission_is_valid_and_requires_review():
    submission = AgentSubmission.model_validate(_empty_submission())

    assert submission.agent_review.required is True
    assert submission.agent_review.severity == "alta"


def test_recompute_validation_uses_configured_value_tolerance():
    submission = deepcopy(FIXTURES["02_banco_meridional_jcp"]["submission"])
    submission["value_or_ratio"]["gross_value"] = 1.0
    submission["value_or_ratio"]["net_value"] = 0.99
    submission["value_or_ratio"]["irrf_rate"] = 0.0

    validation = _recompute_validation(
        submission,
        GOLDEN_PATH,
        {"value_rel_tolerance": 0.001, "value_abs_tolerance": 0.0001},
    )

    assert validation["coherence"]["value"]["max_severity"] == "alta"


def test_critic_document_text_prefers_loop_context(monkeypatch):
    def fail_if_called(_source_file):
        raise AssertionError("read_document should not be called when loop text is available")

    monkeypatch.setattr("src.agent.harness.ing.read_document", fail_if_called)

    assert _critic_document_text("ignored.pdf", {"document_text": "texto OCR"}, Tracer("x", None)) == "texto OCR"


def test_processing_error_yields_escalated_record(tmp_path):
    res = process_document(
        "99_doc_quebrado",
        "data/documents/01_energetica_vale_tiete_dividendo.pdf",
        _BoomClient(),
        _CONFIG,
        tmp_path,
    )

    assert res["outcome"] == "review"
    assert "processing_error" in res["review_reasons"]
    assert res["record"]["review"]["required"] is True
    assert res["record"]["document_id"] == "99_doc_quebrado"


def test_self_consistency_divergence_penalizes_and_escalates():
    from src.agent.harness import _apply_self_consistency_penalty, _flag_self_consistency_review

    confidence = {"confidence_score": 0.9, "drivers": []}
    _apply_self_consistency_penalty(confidence, 0.67)
    assert confidence["confidence_score"] == 0.7

    routing = {"required": False, "reasons": []}
    _flag_self_consistency_review(routing, 0.67)
    assert routing["required"] is True
    assert any(r["code"] == "self_consistency_divergence" for r in routing["reasons"])

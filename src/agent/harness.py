from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ..confidence import compute_confidence
from ..observability import Tracer, now_iso
from ..routing import route
from ..schema import AgentSubmission, Record
from ..tools import ingestion as ing
from ..tools.coherence import check_date_coherence, check_value_coherence
from ..tools.golden import lookup_golden_record
from ..tools.isin import validate_isin
from .critic import run_critic
from .loop import run_agent

SUBMISSION_FIELDS = ("issuer", "cnpj", "isin", "ticker", "event_type", "value_or_ratio", "dates")
SELF_CONSISTENCY_PENALTY = 0.2
SELF_CONSISTENCY_LENSES = (
    "priorize a natureza/substância do provento (dividendo vs JCP) e a classificação.",
    "priorize as datas e a coerência entre bruto, líquido e IRRF.",
    "priorize os identificadores (emissor, ISIN, ticker, CNPJ) e o casamento com a base.",
)


def _empty_field() -> dict[str, Any]:
    return {"value": None, "confidence_score": 0.0}


def _empty_submission() -> dict:
    return AgentSubmission.model_validate(
        {
            "issuer": _empty_field(),
            "cnpj": _empty_field(),
            "isin": _empty_field(),
            "ticker": _empty_field(),
            "event_type": {**_empty_field(), "normalized_code": None},
            "value_or_ratio": {"kind": "none"},
            "dates": {},
            "agent_review": {
                "required": True,
                "severity": "alta",
                "reasons": ["agente não finalizou"],
            },
        }
    ).model_dump()


def _date_values(submission: dict) -> dict:
    return {key: value.get("value") for key, value in submission.get("dates", {}).items()}


def _recompute_validation(submission: dict, golden_path: str, thresholds: dict | None = None) -> dict:
    thresholds = thresholds or {}
    value_or_ratio = submission.get("value_or_ratio", {})
    return {
        "golden_record": lookup_golden_record(
            golden_path,
            isin=(submission.get("isin") or {}).get("value") or "",
            ticker=(submission.get("ticker") or {}).get("value") or "",
            cnpj=(submission.get("cnpj") or {}).get("value") or "",
            issuer=(submission.get("issuer") or {}).get("value") or "",
        ),
        "isin": validate_isin((submission.get("isin") or {}).get("value") or ""),
        "coherence": {
            "dates": check_date_coherence(_date_values(submission)),
            "value": check_value_coherence(
                value_or_ratio.get("kind", "none"),
                value_or_ratio.get("gross_value"),
                value_or_ratio.get("net_value"),
                value_or_ratio.get("irrf_rate"),
                rel_tolerance=thresholds.get("value_rel_tolerance", 0.01),
                abs_tolerance=thresholds.get("value_abs_tolerance", 0.0001),
            ),
        },
    }


def _sc_triggered(submission: dict, ingestion_meta: dict, thresholds: dict) -> bool:
    if ingestion_meta.get("method") == "ocr":
        return True

    low_confidence = thresholds.get("low_confidence_score", 0.6)
    for key in ("issuer", "isin", "ticker", "event_type"):
        if (submission.get(key) or {}).get("confidence_score", 1.0) < low_confidence:
            return True
    return False


def _critic_document_text(source_file: str, loop_result: dict, tracer: Tracer) -> str:
    if loop_result.get("document_text"):
        return loop_result["document_text"]

    try:
        return ing.read_document(source_file)["text"]
    except Exception as exc:
        tracer.log("critic_context_unavailable", reason=str(exc))
        return ""


def _event_type_code(submission: dict | None) -> str | None:
    if not submission:
        return None
    return (submission.get("event_type") or {}).get("normalized_code")


def _run_self_consistency(document_id, source_file, llm, config, submission, ingestion_meta, tracer):
    sc_cfg = config.get("self_consistency", {})
    thresholds = config.get("thresholds", {})
    if not sc_cfg.get("enabled") or not _sc_triggered(submission, ingestion_meta, thresholds):
        return 1, 1.0

    runs = max(1, int(sc_cfg.get("runs", 1)))
    codes = [_event_type_code(submission)]
    for index in range(runs - 1):
        lens = SELF_CONSISTENCY_LENSES[index % len(SELF_CONSISTENCY_LENSES)]
        result = run_agent(document_id, source_file, llm, config, Tracer(document_id, None), lens=lens)
        codes.append(_event_type_code(result.get("submission")))

    agreement = Counter(codes).most_common(1)[0][1] / len(codes) if codes else 1.0
    tracer.self_consistency("event_type.normalized_code", runs, agreement)
    return runs, agreement


def _apply_self_consistency_penalty(confidence: dict, agreement: float) -> None:
    if agreement >= 1.0:
        return
    confidence["confidence_score"] = round(
        max(0.0, confidence["confidence_score"] - SELF_CONSISTENCY_PENALTY),
        3,
    )
    confidence["drivers"].append(f"self-consistency divergente ({agreement:.0%})")


def _flag_self_consistency_review(routing: dict, agreement: float) -> None:
    if agreement >= 1.0:
        return
    routing["required"] = True
    routing["reasons"].append(
        {
            "code": "self_consistency_divergence",
            "severity": "media",
            "detail": f"re-extrações divergiram ({agreement:.0%})",
            "suggested_action": "revisar classificação",
        }
    )


def _record_payload(document_id, source_file, submission, validation, confidence, routing, loop_result,
                    ingestion_meta, critic_verdict, self_consistency_runs, config, tracer):
    provider_config = config.get("providers", {}).get(config["provider"], {})
    return {
        "document_id": document_id,
        "source_file": source_file,
        "ingestion": {
            "method": ingestion_meta.get("method", "text_native"),
            "ocr_engine": ingestion_meta.get("ocr_engine"),
            "pages": ingestion_meta.get("pages"),
            "ocr_confidence": ingestion_meta.get("ocr_confidence"),
        },
        **{field: submission[field] for field in SUBMISSION_FIELDS},
        "currency": submission.get("currency", "BRL"),
        "validation": validation,
        "confidence_overall": confidence,
        "review": routing,
        "agent_audit": {
            "steps": loop_result["steps"],
            "tool_calls": loop_result["tool_calls"],
            "critic_verdict": critic_verdict,
            "self_consistency_runs": self_consistency_runs,
            "tokens": loop_result["tokens"],
            "duration_s": tracer.duration(),
        },
        "extraction_metadata": {
            "provider": config["provider"],
            "model": provider_config.get("model"),
            "prompt_version": config.get("prompt_version"),
            "timestamp": now_iso(),
        },
    }


def _error_result(document_id, source_file, config, exc, tracer) -> dict:
    submission = _empty_submission()
    provider_config = config.get("providers", {}).get(config["provider"], {})
    review = {
        "required": True,
        "severity": "alta",
        "reasons": [{
            "code": "processing_error",
            "severity": "alta",
            "detail": str(exc),
            "suggested_action": "investigar falha de processamento",
        }],
        "suggested_action": "investigar falha de processamento",
    }
    record = Record.model_validate(
        {
            "document_id": document_id,
            "source_file": source_file,
            "ingestion": {"method": "text_native", "ocr_engine": None, "pages": None},
            **{field: submission[field] for field in SUBMISSION_FIELDS},
            "currency": submission.get("currency", "BRL"),
            "validation": {},
            "confidence_overall": {"confidence_score": 0.0, "drivers": ["falha de processamento"]},
            "review": review,
            "agent_audit": {
                "steps": 0, "tool_calls": [], "critic_verdict": None,
                "self_consistency_runs": 0, "tokens": 0, "duration_s": tracer.duration(),
            },
            "extraction_metadata": {
                "provider": config["provider"], "model": provider_config.get("model"),
                "prompt_version": config.get("prompt_version"), "timestamp": now_iso(),
            },
        }
    )
    tracer.final("review", True, ["processing_error"])
    return {
        "record": record.model_dump(),
        "outcome": "review",
        "tokens": 0,
        "steps": 0,
        "tool_calls": 0,
        "duration_s": tracer.duration(),
        "review_reasons": ["processing_error"],
    }


def process_document(document_id, source_file, llm, config, output_dir: Path) -> dict:
    trace_path = output_dir / "traces" / f"{document_id}.jsonl" if config.get("trace") else None
    tracer = Tracer(document_id, trace_path)
    try:
        return _process_document(document_id, source_file, llm, config, tracer)
    except Exception as exc:
        tracer.log("processing_error", reason=str(exc))
        return _error_result(document_id, source_file, config, exc, tracer)


def _process_document(document_id, source_file, llm, config, tracer) -> dict:
    loop_result = run_agent(document_id, source_file, llm, config, tracer)
    submission = loop_result["submission"] or _empty_submission()
    ingestion_meta = loop_result["ingestion"]
    thresholds = config.get("thresholds", {})

    validation = _recompute_validation(submission, config["golden_path"], thresholds)

    critic_verdict = None
    if config.get("critic", {}).get("enabled"):
        critic_verdict = run_critic(
            llm,
            _critic_document_text(source_file, loop_result, tracer),
            submission,
            tracer,
        )

    self_consistency_runs, self_consistency_agreement = 1, 1.0
    if loop_result["terminated"]:
        self_consistency_runs, self_consistency_agreement = _run_self_consistency(
            document_id,
            source_file,
            llm,
            config,
            submission,
            ingestion_meta,
            tracer,
        )

    confidence = compute_confidence(
        submission,
        validation,
        ingestion_meta,
        critic_verdict,
        thresholds,
    )
    _apply_self_consistency_penalty(confidence, self_consistency_agreement)

    routing = route(
        submission,
        validation,
        ingestion_meta,
        confidence,
        critic_verdict,
        loop_result["terminated"],
        thresholds,
    )
    _flag_self_consistency_review(routing, self_consistency_agreement)

    record = Record.model_validate(
        _record_payload(
            document_id,
            source_file,
            submission,
            validation,
            confidence,
            routing,
            loop_result,
            ingestion_meta,
            critic_verdict,
            self_consistency_runs,
            config,
            tracer,
        )
    )

    outcome = "review" if routing["required"] else "auto_approved"
    tracer.final(outcome, routing["required"], [reason["code"] for reason in routing["reasons"]])
    return {
        "record": record.model_dump(),
        "outcome": outcome,
        "tokens": loop_result["tokens"],
        "steps": loop_result["steps"],
        "tool_calls": len(loop_result["tool_calls"]),
        "duration_s": tracer.duration(),
        "review_reasons": [reason["code"] for reason in routing["reasons"]],
    }

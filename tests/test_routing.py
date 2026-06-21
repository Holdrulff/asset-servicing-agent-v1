from copy import deepcopy

from src.routing import route


def _clean() -> dict:
    field = {"value": "X", "confidence_score": 0.95}
    return deepcopy({
        "submission": {
            "issuer": field, "cnpj": field, "isin": field, "ticker": field,
            "event_type": {"value": "Dividendo", "confidence_score": 0.95,
                           "normalized_code": "DIVIDENDO", "title_vs_substance_conflict": False},
            "value_or_ratio": {"kind": "cash_per_share"},
            "dates": {"data_com": {"value": "12/06/2026"}, "payment": {"value": "03/07/2026"}},
            "agent_review": {"required": False, "severity": "none", "reasons": []},
        },
        "validation": {
            "golden_record": {"status": "matched"},
            "isin": {"format_valid": True, "check_digit_valid": False},
            "coherence": {"dates": {"violations": [], "max_severity": "none"},
                          "value": {"violations": [], "max_severity": "none"}},
        },
        "ingestion_meta": {"method": "text_native"},
        "confidence": {"confidence_score": 0.9, "drivers": []},
        "critic_verdict": {"veredito_geral": "ok", "campos": []},
        "terminated": True,
        "thresholds": {"low_confidence_score": 0.6},
    })


def _run(cfg):
    result = route(**cfg)
    return result["required"], {reason["code"] for reason in result["reasons"]}


def test_clean_doc_auto_approves():
    required, codes = _run(_clean())
    assert required is False
    assert codes == set()


def test_synthetic_isin_check_digit_does_not_escalate():
    # isin format_valid mas check_digit_valid=False (lote sintético) não deve reprovar sozinho
    cfg = _clean()
    required, codes = _run(cfg)
    assert required is False and "isin_invalid" not in codes


def test_golden_unmatched_escalates():
    cfg = _clean()
    cfg["validation"]["golden_record"] = {"status": "unmatched"}
    required, codes = _run(cfg)
    assert required and "golden_unmatched" in codes


def test_ocr_origin_escalates():
    cfg = _clean()
    cfg["ingestion_meta"] = {"method": "ocr"}
    required, codes = _run(cfg)
    assert required and "ocr_origin" in codes


def test_title_substance_conflict_escalates():
    cfg = _clean()
    cfg["submission"]["event_type"]["title_vs_substance_conflict"] = True
    required, codes = _run(cfg)
    assert required and "title_substance_conflict" in codes


def test_date_incoherence_escalates():
    cfg = _clean()
    cfg["validation"]["coherence"]["dates"] = {
        "violations": [{"rule": "ordering", "severity": "alta", "detail": "pagamento antes do ex"}],
        "max_severity": "alta",
    }
    required, codes = _run(cfg)
    assert required and "date_incoherence" in codes


def test_missing_payment_escalates():
    cfg = _clean()
    cfg["submission"]["dates"] = {"data_com": {"value": "12/06/2026"}, "payment": {"value": None}}
    required, codes = _run(cfg)
    assert required and "missing_required" in codes


def test_low_confidence_escalates():
    cfg = _clean()
    cfg["confidence"] = {"confidence_score": 0.4, "drivers": []}
    required, codes = _run(cfg)
    assert required and "low_confidence" in codes


def test_critic_suspeito_escalates():
    cfg = _clean()
    cfg["critic_verdict"] = {"veredito_geral": "suspeito",
                             "campos": [{"campo": "isin", "concorda": False}]}
    required, codes = _run(cfg)
    assert required and "critic_disagreed" in codes


def test_budget_exceeded_escalates():
    cfg = _clean()
    cfg["terminated"] = False
    required, codes = _run(cfg)
    assert required and "budget_exceeded" in codes

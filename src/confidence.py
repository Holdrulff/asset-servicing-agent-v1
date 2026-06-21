from __future__ import annotations

_FIELD_KEYS = ["issuer", "cnpj", "isin", "ticker", "event_type"]
OCR_SCORE_CEILING = 0.79


def _score_of(field: dict) -> float:
    s = field.get("confidence_score")
    return float(s) if isinstance(s, (int, float)) else 0.5


def compute_confidence(submission, validation, ingestion_meta, critic_verdict, thresholds) -> dict:
    drivers = []
    scores = [_score_of(submission[k]) for k in _FIELD_KEYS if k in submission]
    scores.append(_score_of(submission.get("value_or_ratio", {})))
    base = sum(scores) / len(scores) if scores else 0.5

    g = validation.get("golden_record", {})
    if g.get("status") == "matched":
        base += 0.05
        drivers.append("golden: matched (+)")
    elif g.get("status") == "partial":
        base -= 0.15
        drivers.append("golden: partial (-)")
    elif g.get("status") == "unmatched":
        base -= 0.30
        drivers.append("golden: unmatched (--)")

    isin_v = validation.get("isin", {})
    if not isin_v.get("format_valid", True):
        base -= 0.25
        drivers.append("isin: formato inválido (--)")
    elif isin_v.get("check_digit_valid") is False:
        drivers.append("isin: dígito não confere (warning, lote sintético)")

    coh = validation.get("coherence", {})
    if (coh.get("dates", {}).get("max_severity") == "alta" or
            coh.get("value", {}).get("max_severity") == "alta"):
        base -= 0.30
        drivers.append("coerência: violação alta (--)")

    ocr = ingestion_meta.get("method") == "ocr"
    if ocr:
        base -= 0.15
        drivers.append("origem OCR: confiança limitada")

    if critic_verdict and critic_verdict.get("rebaixar_confianca"):
        base -= 0.15
        drivers.append("crítico: rebaixou confiança")

    score = max(0.0, min(1.0, base))
    if ocr:
        score = min(score, OCR_SCORE_CEILING)

    return {"confidence_score": round(score, 3), "drivers": drivers}

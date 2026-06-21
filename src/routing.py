from __future__ import annotations

_SEV_ORDER = {"none": 0, "baixa": 1, "media": 2, "alta": 3}
_CASH_CODES = {"DIVIDENDO", "JCP"}
_RATIO_CODES = {"BONIFICACAO", "GRUPAMENTO", "DESDOBRAMENTO"}


def _null(field) -> bool:
    return not field or field.get("value") in (None, "", "null")


def route(submission, validation, ingestion_meta, confidence, critic_verdict,
          terminated, thresholds) -> dict:
    reasons = []

    def add(code, severity, detail, action):
        reasons.append({"code": code, "severity": severity, "detail": detail, "suggested_action": action})

    if not terminated:
        add("budget_exceeded", "alta", "agente não finalizou dentro do orçamento de passos",
            "revisar manualmente do zero")

    g = validation.get("golden_record", {})
    if g.get("status") == "unmatched":
        add("golden_unmatched", "alta", "emissor/ISIN/ticker não constam na base de referência",
            "confirmar cadastro do emissor antes de processar")
    elif g.get("status") == "partial":
        add("golden_partial", "media", f"divergências: {g.get('discrepancies')}",
            "conferir identificadores contra a base")

    isin_v = validation.get("isin", {})
    if not isin_v.get("format_valid", True):
        add("isin_invalid", "alta", "ISIN com formato inválido", "corrigir/confirmar ISIN")

    coh = validation.get("coherence", {})
    for sev in ("alta", "media"):
        for v in coh.get("dates", {}).get("violations", []):
            if v.get("severity") == sev:
                add("date_incoherence", sev, v.get("detail"), "reler datas no aviso / conciliar")
    if coh.get("value", {}).get("max_severity") == "alta":
        add("value_incoherence", "alta", coh["value"]["violations"][0]["detail"], "recalcular bruto/líquido")
    elif coh.get("value", {}).get("max_severity") == "media":
        add("value_incoherence", "media", coh["value"]["violations"][0]["detail"], "conferir valor")

    et = submission.get("event_type", {})
    if et.get("title_vs_substance_conflict"):
        add("title_substance_conflict", "alta",
            f"titulado '{et.get('value')}' mas substância {et.get('normalized_code')}",
            "confirmar natureza do provento (impacto tributário)")

    for key in ("issuer", "isin", "ticker"):
        if _null(submission.get(key)):
            add("missing_required", "alta", f"campo obrigatório ausente: {key}", "obter do aviso/cadastro")

    code = et.get("normalized_code")
    dates = submission.get("dates", {})
    if code in _CASH_CODES:
        if _null(dates.get("payment")):
            add("missing_required", "media", "data de pagamento ausente", "aguardar aviso complementar")
        if _null(dates.get("data_com")):
            add("missing_required", "media", "data com ausente", "obter do aviso")
    if code in _RATIO_CODES and not (submission.get("value_or_ratio", {}) or {}).get("ratio"):
        add("missing_required", "media", "proporção ausente", "obter do aviso")

    if ingestion_meta.get("method") == "ocr":
        add("ocr_origin", "media", "documento escaneado (OCR) — extração não confirmada por texto nativo",
            "validar campos contra o digitalizado")

    score = confidence.get("confidence_score", 1.0)
    if score < thresholds.get("low_confidence_score", 0.6):
        add("low_confidence", "media", f"confiança agregada baixa (score={score})",
            "revisão humana dos campos de baixa confiança")

    if critic_verdict and critic_verdict.get("veredito_geral") == "suspeito":
        suspects = [c["campo"] for c in critic_verdict.get("campos", []) if not c.get("concorda")]
        add("critic_disagreed", "media", f"crítico marcou suspeitos: {suspects}", "rever campos apontados")

    ar = submission.get("agent_review", {})
    if ar.get("required"):
        for r in ar.get("reasons", []):
            add("agent_flagged", ar.get("severity", "media"), r, "rever conforme apontado pelo agente")

    required = len(reasons) > 0
    severity = max(reasons, key=lambda r: _SEV_ORDER.get(r["severity"], 0))["severity"] if reasons else "none"
    action = reasons[0]["suggested_action"] if reasons else "auto-aprovar"
    return {"required": required, "severity": severity, "reasons": reasons, "suggested_action": action}

from __future__ import annotations


def _fn(name, description, properties, required=None):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": required or [], "additionalProperties": True}}}


_SCORE = {"type": "number", "minimum": 0, "maximum": 1,
          "description": "confiança numérica 0..1 (1=certeza máxima)"}

_FIELD = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "confidence_score": _SCORE,
        "source_text": {"type": ["string", "null"], "description": "trecho verbatim do aviso"},
        "source_location": {"type": ["string", "null"], "description": "tabela|corpo|cabeçalho"},
        "rationale": {"type": ["string", "null"]},
    },
    "required": ["value", "confidence_score"],
}

_DATE = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"], "description": "dd/mm/yyyy ou null se ausente"},
        "confidence_score": _SCORE,
        "source_text": {"type": ["string", "null"]},
        "source_location": {"type": ["string", "null"]},
        "rationale": {"type": ["string", "null"]},
    },
}

TOOLS = [
    _fn("read_document", "Lê o texto nativo de um PDF. Use primeiro. Retorna has_text_layer.",
        {"pdf_path": {"type": "string"}}, ["pdf_path"]),
    _fn("read_page", "Relê UMA página (1-indexed) para reconciliar uma checagem que falhou.",
        {"pdf_path": {"type": "string"}, "page_number": {"type": "integer"}}, ["pdf_path", "page_number"]),
    _fn("run_ocr", "OCR (RapidOCR) — só quando read_document retornar has_text_layer=false.",
        {"pdf_path": {"type": "string"}}, ["pdf_path"]),
    _fn("validate_isin", "Valida formato + dígito mod-10 de um ISIN.",
        {"isin": {"type": "string"}}, ["isin"]),
    _fn("lookup_golden_record",
        "Casa o registro contra a base de referência por ISIN/ticker/CNPJ/emissor (cross-check).",
        {"isin": {"type": "string"}, "ticker": {"type": "string"},
         "cnpj": {"type": "string"}, "issuer": {"type": "string"}}, []),
    _fn("check_date_coherence",
        "Valida ordenação aprovação<=data_com<=ex<=pagamento e plausibilidade.",
        {"dates": {"type": "object", "description": "{approval,data_com,ex,payment: 'dd/mm/yyyy'}"}}, ["dates"]),
    _fn("check_value_coherence",
        "Valida líquido≈bruto×(1-irrf); proporção não deve ter caixa.",
        {"kind": {"type": "string", "enum": ["cash_per_share", "ratio", "none"]},
         "gross_value": {"type": ["number", "null"]}, "net_value": {"type": ["number", "null"]},
         "irrf_rate": {"type": ["number", "null"], "description": "fração: 0.175"}}, ["kind"]),
    _fn("log_reasoning",
        "OBSERVABILIDADE: registre seu plano/reflexão (auditável no trace). Não altera dados.",
        {"thought": {"type": "string"}, "phase": {"type": "string"}}, ["thought"]),
    _fn("submit_record",
        "AÇÃO TERMINAL. Só após rodar as validações. Submete o registro estruturado final.",
        {
            "issuer": _FIELD, "cnpj": _FIELD, "isin": _FIELD, "ticker": _FIELD,
            "event_type": {"type": "object", "properties": {
                **_FIELD["properties"],
                "normalized_code": {"type": "string",
                                    "enum": ["DIVIDENDO", "JCP", "BONIFICACAO", "GRUPAMENTO", "DESDOBRAMENTO"]},
                "classification_evidence": {"type": "array", "items": {"type": "string"}},
                "title_vs_substance_conflict": {"type": "boolean"}}},
            "currency": {"type": "string"},
            "value_or_ratio": {"type": "object", "properties": {
                "kind": {"type": "string", "enum": ["cash_per_share", "ratio", "none"]},
                "gross_value": {"type": ["number", "null"]}, "irrf_rate": {"type": ["number", "null"]},
                "net_value": {"type": ["number", "null"]}, "ratio": {"type": ["string", "null"]},
                "confidence_score": _SCORE, "source_text": {"type": ["string", "null"]},
                "source_location": {"type": ["string", "null"]},
                "rationale": {"type": ["string", "null"]}}},
            "dates": {"type": "object", "additionalProperties": _DATE},
            "agent_review": {"type": "object", "properties": {
                "required": {"type": "boolean"},
                "severity": {"type": "string", "enum": ["none", "baixa", "media", "alta"]},
                "reasons": {"type": "array", "items": {"type": "string"}}}},
            "overall_rationale": {"type": "string"},
        },
        ["issuer", "isin", "ticker", "event_type", "value_or_ratio", "dates"]),
]

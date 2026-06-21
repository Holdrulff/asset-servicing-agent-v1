# Fixtures offline do provider `replay` (NÃO é extração do modelo real).
from __future__ import annotations

from pathlib import Path as _Path

DOCS = "data/documents"

_LEVEL = {"alta": 0.95, "media": 0.6, "baixa": 0.4}


def _f(value, conf="alta", score=None, src=None, loc="corpo", rat=None):
    return {"value": value, "confidence_score": score if score is not None else _LEVEL[conf],
            "source_text": src, "source_location": loc, "rationale": rat}


def _d(value, conf="alta", src=None, rat=None):
    return {"value": value, "confidence_score": _LEVEL[conf],
            "source_text": src, "source_location": "corpo", "rationale": rat}


FIXTURES = {
    "01": {
        "path": f"{DOCS}/01_energetica_vale_tiete_dividendo.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Energética Vale do Tietê S.A.", loc="cabeçalho"),
            "cnpj": _f("12.345.678/0001-90"),
            "isin": _f("BRTIETACNOR3"),
            "ticker": _f("TIET3"),
            "event_type": {**_f("Pagamento de Dividendos"), "normalized_code": "DIVIDENDO",
                           "classification_evidence": ["distribuição de dividendos"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "cash_per_share", "gross_value": 0.4275, "irrf_rate": None,
                               "net_value": None, "ratio": None, "confidence_score": 0.95,
                               "source_text": "R$ 0,4275000000 por ação ON",
                               "rationale": "IRRF 10% condicional ao excedente de R$50k/mês"},
            "dates": {"approval": _d("28/05/2026"), "data_com": _d("12/06/2026"),
                      "ex": _d("15/06/2026"), "payment": _d("03/07/2026")},
            "agent_review": {"required": False, "severity": "none", "reasons": []},
            "overall_rationale": "Dividendo limpo, casa com golden.",
        },
    },
    "02": {
        "path": f"{DOCS}/02_banco_meridional_jcp.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Banco Meridional do Brasil S.A.", loc="cabeçalho"),
            "cnpj": _f("60.111.222/0001-55"),
            "isin": _f("BRBMRDACNPR7"),
            "ticker": _f("BMRD4"),
            "event_type": {**_f("Juros sobre o Capital Próprio (JCP)"), "normalized_code": "JCP",
                           "classification_evidence": ["juros sobre o capital próprio", "art. 9º Lei 9.249/95"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "cash_per_share", "gross_value": 0.1738420000, "irrf_rate": 0.175,
                               "net_value": 0.1434196500, "ratio": None, "confidence_score": 0.95,
                               "source_text": "R$ 0,1738420000 bruto; R$ 0,1434196500 líquido",
                               "rationale": "IRRF 17,5% sobre JCP"},
            "dates": {"approval": _d("02/06/2026"), "data_com": _d("16/06/2026"),
                      "ex": _d("17/06/2026"), "payment": _d("14/08/2026")},
            "agent_review": {"required": False, "severity": "none", "reasons": []},
            "overall_rationale": "JCP limpo; bruto→líquido confere (×0,825).",
        },
    },
    "03": {
        "path": f"{DOCS}/03_siderurgica_paranaense_proventos.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Companhia Siderúrgica Paranaense S.A.", loc="cabeçalho"),
            "cnpj": _f("76.543.210/0001-12"),
            "isin": _f("BRCSPRACNOR1"),
            "ticker": _f("CSPR3"),
            "event_type": {**_f("Distribuição de Dividendos", conf="media", score=0.65),
                           "normalized_code": "JCP",
                           "classification_evidence": [
                               "remuneração do capital próprio",
                               "limitados à variação pro rata die da Taxa de Juros de Longo Prazo (TJLP)"],
                           "title_vs_substance_conflict": True,
                           "rationale": "Título diz 'dividendos' mas a substância (TJLP, remuneração do "
                                        "capital próprio) é JCP — classificar por substância."},
            "currency": "BRL",
            "value_or_ratio": {"kind": "cash_per_share", "gross_value": 0.0921500000, "irrf_rate": 0.175,
                               "net_value": 0.0760237500, "ratio": None, "confidence_score": 0.95,
                               "source_text": "R$ 0,0921500000 bruto; R$ 0,0760237500 líquido",
                               "rationale": "IRRF 17,5% — consistente com JCP, não dividendo"},
            "dates": {"approval": _d("05/06/2026"), "data_com": _d("19/06/2026"),
                      "ex": _d("22/06/2026"), "payment": _d("11/09/2026")},
            "agent_review": {"required": True, "severity": "alta",
                             "reasons": ["conflito título×substância: titulado dividendo, substância JCP"]},
            "overall_rationale": "Armadilha de classificação: substância JCP apesar do título.",
        },
    },
    "04": {
        "path": f"{DOCS}/04_rede_varejo_jcp_sem_data.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Rede Varejo Brasil S.A.", loc="cabeçalho"),
            "cnpj": _f("08.777.666/0001-33"),
            "isin": _f("BRRVBRACNOR9"),
            "ticker": _f("RVBR3"),
            "event_type": {**_f("Juros sobre o Capital Próprio"), "normalized_code": "JCP",
                           "classification_evidence": ["juros sobre o capital próprio"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "cash_per_share", "gross_value": 0.2050000000, "irrf_rate": 0.175,
                               "net_value": 0.1691250000, "ratio": None, "confidence_score": 0.95,
                               "source_text": "R$ 0,2050000000 bruto; R$ 0,1691250000 líquido"},
            "dates": {"approval": _d("09/06/2026"), "data_com": _d("23/06/2026"),
                      "ex": _d("24/06/2026"),
                      "payment": _d(None, conf="baixa", src="A definir (vide aviso complementar)",
                                    rat="Data de pagamento não divulgada")},
            "agent_review": {"required": True, "severity": "media",
                             "reasons": ["campo obrigatório ausente: data de pagamento ('A definir')"]},
            "overall_rationale": "JCP com data de pagamento ausente.",
        },
    },
    "05": {
        "path": f"{DOCS}/05_aurora_saneamento_dividendo_datas.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Aurora Saneamento S.A.", loc="cabeçalho"),
            "cnpj": _f("22.333.444/0001-77"),
            "isin": _f("BRAURSACNOR4"),
            "ticker": _f("AURS3"),
            "event_type": {**_f("Dividendos Intercalares"), "normalized_code": "DIVIDENDO",
                           "classification_evidence": ["dividendos intercalares"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "cash_per_share", "gross_value": 0.3100, "irrf_rate": None,
                               "net_value": None, "ratio": None, "confidence_score": 0.95,
                               "source_text": "R$ 0,3100000000 por ação ON"},
            "dates": {"approval": _d("01/06/2026"), "data_com": _d("15/07/2026"),
                      "ex": _d("16/07/2026"),
                      "payment": _d("10/07/2026", rat="Pagamento antes do ex — incoerência")},
            "agent_review": {"required": True, "severity": "alta",
                             "reasons": ["incoerência de datas: pagamento 10/07 antes do ex 16/07"]},
            "overall_rationale": "Violação de coerência temporal.",
        },
    },
    "06": {
        "path": f"{DOCS}/06_petroquimica_litoral_grupamento.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Petroquímica Litoral S.A.", loc="cabeçalho"),
            "cnpj": _f("55.666.777/0001-08"),
            "isin": _f("BRPQLTACNOR8"),
            "ticker": _f("PQLT3"),
            "event_type": {**_f("Grupamento de Ações (Inplit)"), "normalized_code": "GRUPAMENTO",
                           "classification_evidence": ["grupamento de ações", "inplit", "10 para 1"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "ratio", "gross_value": None, "irrf_rate": None,
                               "net_value": None, "ratio": "10:1", "confidence_score": 0.95,
                               "source_text": "grupamento na proporção de 10:1",
                               "rationale": "Evento de proporção, sem valor monetário"},
            "dates": {"approval": _d("30/05/2026"), "data_com": _d("26/06/2026")},
            "agent_review": {"required": False, "severity": "none", "reasons": []},
            "overall_rationale": "Grupamento 10:1, sem caixa.",
        },
    },
    "07": {
        "path": f"{DOCS}/07_telecom_norte_jcp_SCAN.pdf", "scanned": True,
        "submission": {
            "issuer": _f("Telecom Norte Participações S.A.", conf="baixa", score=0.5, loc="ocr"),
            "cnpj": _f("33.222.111/0001-44", conf="baixa", score=0.5, loc="ocr"),
            "isin": _f("BRTLNRACNPR2", conf="baixa", score=0.5, loc="ocr"),
            "ticker": _f("TLNR4", conf="baixa", score=0.5, loc="ocr"),
            "event_type": {**_f("Juros sobre o Capital Próprio", conf="baixa", score=0.5, loc="ocr"),
                           "normalized_code": "JCP",
                           "classification_evidence": ["juros sobre o capital próprio (via OCR)"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "cash_per_share", "gross_value": None, "irrf_rate": 0.175,
                               "net_value": None, "ratio": None, "confidence_score": 0.4,
                               "rationale": "Documento escaneado — valores não confirmados por OCR"},
            "dates": {"data_com": _d("19/06/2026", conf="baixa", rat="OCR")},
            "agent_review": {"required": True, "severity": "media",
                             "reasons": ["origem OCR (documento escaneado) — confiança limitada"]},
            "overall_rationale": "Aviso escaneado; exige OCR e revisão humana.",
        },
    },
    "08": {
        "path": f"{DOCS}/08_construtora_horizonte_bonificacao.pdf", "scanned": False,
        "submission": {
            "issuer": _f("Construtora Horizonte S.A.", loc="cabeçalho"),
            "cnpj": _f("09.888.999/0001-21"),
            "isin": _f("BRCNHZACNOR5"),
            "ticker": _f("CNHZ3"),
            "event_type": {**_f("Bonificação em Ações"), "normalized_code": "BONIFICACAO",
                           "classification_evidence": ["bonificação em ações", "capitalização de reservas"],
                           "title_vs_substance_conflict": False},
            "currency": "BRL",
            "value_or_ratio": {"kind": "ratio", "gross_value": None, "irrf_rate": None,
                               "net_value": None, "ratio": "1:20", "confidence_score": 0.95,
                               "source_text": "1 ação nova para cada 20 ações",
                               "rationale": "Bonificação 5%; custo atribuído R$ 7,82/ação"},
            "dates": {"approval": _d("04/06/2026"), "data_com": _d("18/06/2026"),
                      "ex": _d("19/06/2026")},
            "agent_review": {"required": True, "severity": "media",
                             "reasons": ["emissor/ISIN/ticker ausentes na base de referência"]},
            "overall_rationale": "Bonificação de emissor fora do golden_records.",
        },
    },
}

FIXTURES = {_Path(fx["path"]).stem: fx for fx in FIXTURES.values()}

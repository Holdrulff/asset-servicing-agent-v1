from __future__ import annotations

from pathlib import Path


def _label(score) -> str:
    if not isinstance(score, (int, float)):
        return "?"
    return "alta" if score >= 0.8 else "media" if score >= 0.6 else "baixa"


def _confidence(record: dict) -> dict:
    return record.get("confidence_overall", {})


def _review_reasons(record: dict) -> list[dict]:
    return record.get("review", {}).get("reasons", [])


def _reason_codes(record: dict) -> str:
    codes = sorted({reason.get("code", "unknown") for reason in _review_reasons(record)})
    return ", ".join(codes) or "—"


def _md_cell(value) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def _row(record: dict) -> dict:
    event_type = record.get("event_type", {})
    score = _confidence(record).get("confidence_score", "?")
    return {
        "doc": record["document_id"],
        "issuer": (record.get("issuer") or {}).get("value", "?"),
        "event": event_type.get("normalized_code") or event_type.get("value", "?"),
        "confidence": f"{_label(score)} ({score})",
        "review": bool(record.get("review", {}).get("required")),
        "codes": _reason_codes(record),
    }


def _sorted(records: list[dict]) -> list[dict]:
    return sorted(records, key=lambda record: record["document_id"])


def _write_md(records, auto, review, output_dir: Path) -> None:
    lines = [
        "# Relatório de Exceções — Asset Servicing\n",
        f"Total: {len(records)} | Auto-aprovados: {len(auto)} | Em revisão: {len(review)}\n",
        "\n## Resumo do lote\n",
        "| Doc | Emissor | Evento | Confiança | Desfecho | Motivos |",
        "|-----|---------|--------|-----------|----------|---------|",
    ]
    for record in _sorted(records):
        row = _row(record)
        outcome = "🔴 REVIEW" if row["review"] else "🟢 auto"
        lines.append(
            f"| {_md_cell(row['doc'])} | {_md_cell(row['issuer'])} | {_md_cell(row['event'])} "
            f"| {_md_cell(row['confidence'])} | {outcome} | {_md_cell(row['codes'])} |"
        )

    lines.append("\n## Documentos em revisão (detalhe)\n")
    for record in _sorted(review):
        review_block = record["review"]
        issuer = (record.get("issuer") or {}).get("value", "?")
        lines.append(
            f"### {record['document_id']} — {issuer} "
            f"(severidade: {review_block['severity']})"
        )
        lines.append(f"- Ação sugerida: **{review_block.get('suggested_action', '?')}**")
        for reason in _review_reasons(record):
            lines.append(f"- [{reason['severity']}] `{reason['code']}` — {reason['detail']}")
        lines.append("")

    (output_dir / "exceptions_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_report(records: list[dict], output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    review = [record for record in records if record.get("review", {}).get("required")]
    auto = [record for record in records if not record.get("review", {}).get("required")]

    _write_md(records, auto, review, output_dir)

    return {
        "total": len(records),
        "auto_approved": [record["document_id"] for record in auto],
        "review": [
            {
                "document_id": record["document_id"],
                "severity": record["review"]["severity"],
                "reasons": [reason["code"] for reason in record["review"]["reasons"]],
            }
            for record in review
        ],
    }

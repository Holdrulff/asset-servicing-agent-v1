from src.output.report import build_report


def _record(document_id: str, review_required: bool) -> dict:
    return {
        "document_id": document_id,
        "issuer": {"value": "Emissor | Teste"},
        "event_type": {"normalized_code": "DIVIDENDO"},
        "confidence_overall": {"confidence_score": 0.91},
        "review": {
            "required": review_required,
            "severity": "media" if review_required else "none",
            "suggested_action": "conferir" if review_required else "auto-aprovar",
            "reasons": [
                {"code": "low_confidence", "severity": "media",
                 "detail": "score baixo", "suggested_action": "conferir"}
            ] if review_required else [],
        },
    }


def test_build_report_returns_summary_and_escapes_markdown(tmp_path):
    summary = build_report([_record("doc_auto", False), _record("doc_review", True)], tmp_path)

    assert summary["total"] == 2
    assert summary["auto_approved"] == ["doc_auto"]
    assert summary["review"][0]["document_id"] == "doc_review"

    report_md = (tmp_path / "exceptions_report.md").read_text(encoding="utf-8")
    assert "Emissor \\| Teste" in report_md

    # poda: relatório só em .md (sem .docx / .json)
    assert not (tmp_path / "exceptions_report.json").exists()
    assert not (tmp_path / "exceptions_report.docx").exists()

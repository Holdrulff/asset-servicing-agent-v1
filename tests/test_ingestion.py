from src.tools.ingestion import run_ocr


def test_run_ocr_reports_confidence():
    result = run_ocr("data/documents/07_telecom_norte_jcp_SCAN.pdf")

    assert result["available"] is True
    assert isinstance(result["ocr_confidence"], float)
    assert 0.0 <= result["ocr_confidence"] <= 1.0

from pathlib import Path

from src.agent.harness import process_document
from src.llm.replay_client import ReplayClient

CONFIG = {
    "golden_path": "data/golden_records/golden records.csv",
    "max_steps": 12,
    "ocr": {"lang": "por"},
    "providers": {"replay": {"model": "replay-fixtures"}},
    "provider": "replay",
    "prompt_version": "test",
    "thresholds": {"low_confidence_score": 0.6},
    "self_consistency": {"enabled": False},   # determinístico no replay; off = teste rápido (sem re-OCR)
    "critic": {"enabled": True},
}

EXPECTED_AUTO = {
    "01_energetica_vale_tiete_dividendo",
    "02_banco_meridional_jcp",
    "06_petroquimica_litoral_grupamento",
}


def test_replay_batch_matches_expected_outcomes(tmp_path):
    docs = sorted(Path("data/documents").glob("*.pdf"))
    assert docs, "sem PDFs em data/documents"

    llm = ReplayClient()
    outcomes = {pdf.stem: process_document(pdf.stem, str(pdf), llm, CONFIG, tmp_path)["outcome"]
                for pdf in docs}

    auto = {doc for doc, outcome in outcomes.items() if outcome == "auto_approved"}
    review = {doc for doc, outcome in outcomes.items() if outcome == "review"}

    assert auto == EXPECTED_AUTO, f"auto-aprovados inesperados: {auto}"
    assert review == set(outcomes) - EXPECTED_AUTO
    assert len(outcomes) == len(docs)   # completude: todo doc gerou desfecho

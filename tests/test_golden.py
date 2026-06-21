from src.tools.golden import lookup_golden_record

G = "data/golden_records/golden records.csv"


def test_doc01_matched():
    r = lookup_golden_record(G, isin="BRTIETACNOR3", ticker="TIET3",
                             cnpj="12.345.678/0001-90", issuer="Energética Vale do Tietê S.A.")
    assert r["status"] == "matched"


def test_doc08_unmatched():
    r = lookup_golden_record(G, isin="BRCNHZACNOR5", ticker="CNHZ3",
                             cnpj="09.888.999/0001-21", issuer="Construtora Horizonte S.A.")
    assert r["status"] == "unmatched"


def test_partial_when_ticker_diverges():
    r = lookup_golden_record(G, isin="BRTIETACNOR3", ticker="WRONG9")
    assert r["status"] == "partial"
    assert any("ticker" in d for d in r["discrepancies"])

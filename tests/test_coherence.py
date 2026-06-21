from src.tools.coherence import check_date_coherence, check_value_coherence


def test_doc05_payment_before_ex_is_high_severity():
    r = check_date_coherence({"approval": "01/06/2026", "data_com": "15/07/2026",
                              "ex": "16/07/2026", "payment": "10/07/2026"})
    assert r["max_severity"] == "alta"
    assert any(v["rule"] == "ordering" for v in r["violations"])


def test_clean_dates_ok():
    r = check_date_coherence({"approval": "28/05/2026", "data_com": "12/06/2026",
                              "ex": "15/06/2026", "payment": "03/07/2026"})
    assert r["ok"]


def test_doc02_value_net_matches():
    r = check_value_coherence("cash_per_share", 0.1738420000, 0.1434196500, 0.175)
    assert r["ok"]


def test_value_mismatch_flagged():
    r = check_value_coherence("cash_per_share", 1.0, 0.9, 0.175)  # esperado 0.825
    assert r["max_severity"] == "alta"


def test_ratio_event_should_not_have_cash():
    r = check_value_coherence("ratio", gross_value=0.5)
    assert r["violations"]

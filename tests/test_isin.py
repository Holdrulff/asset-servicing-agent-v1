from src.tools.isin import validate_isin


def test_real_isin_check_digit_valid():
    # Apple US0378331005 é um ISIN real e válido (mod-10)
    r = validate_isin("US0378331005", expected_country=None)
    assert r["format_valid"] and r["check_digit_valid"]


def test_synthetic_isin_is_format_only():
    # ISINs do lote são sintéticos: formato ok, dígito não confere
    r = validate_isin("BRTIETACNOR3")
    assert r["format_valid"] and r["check_digit_valid"] is False
    assert r["status"] == "format_only"


def test_malformed_isin_fails():
    assert validate_isin("BR123")["format_valid"] is False

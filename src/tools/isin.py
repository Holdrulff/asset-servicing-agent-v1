from __future__ import annotations


def _expand(isin: str) -> str:
    out = []
    for ch in isin:
        out.append(str(ord(ch) - 55) if ch.isalpha() else ch)
    return "".join(out)


def _luhn_ok(number: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_isin(isin: str, expected_country: str = "BR") -> dict:
    raw = (isin or "").strip().upper()
    country = raw[:2] if len(raw) >= 2 else ""

    format_valid = (
        len(raw) == 12
        and raw[:2].isalpha()
        and raw[2:11].isalnum()
        and raw[11].isdigit()
    )
    if not format_valid:
        return {"isin": raw, "format_valid": False, "check_digit_valid": False,
                "country": country, "status": "invalid",
                "reason": "formato inválido (esperado: 2 letras país + 9 alfanum + 1 dígito)"}

    check_digit_valid = _luhn_ok(_expand(raw))
    country_ok = (expected_country is None) or (country == expected_country)
    status = "valid" if (check_digit_valid and country_ok) else "format_only"

    return {
        "isin": raw,
        "format_valid": True,
        "check_digit_valid": check_digit_valid,
        "country": country,
        "country_ok": country_ok,
        "status": status,
    }

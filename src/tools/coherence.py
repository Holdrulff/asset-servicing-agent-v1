from __future__ import annotations

from datetime import datetime

_DATE_ORDER = ["approval", "data_com", "ex", "payment"]


def _parse(d: str):
    if not d:
        return None
    d = str(d).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except ValueError:
            continue
    return None


def _max_severity(violations: list) -> str:
    order = {"alta": 3, "media": 2, "baixa": 1}
    if not violations:
        return "none"
    return max(violations, key=lambda v: order.get(v["severity"], 0))["severity"]


def check_date_coherence(dates: dict) -> dict:
    parsed = {k: _parse(dates.get(k)) for k in _DATE_ORDER}
    checks, violations = [], []

    for k in [k for k in _DATE_ORDER if dates.get(k) and parsed[k] is None]:
        violations.append({"rule": "date_parse", "field": k, "severity": "media",
                           "detail": f"data '{dates.get(k)}' não parseável"})

    present = [(k, parsed[k]) for k in _DATE_ORDER if parsed[k] is not None]
    for (k1, d1), (k2, d2) in zip(present, present[1:]):
        if d1 <= d2:
            checks.append({"rule": "ordering", "pair": f"{k1}<={k2}", "ok": True})
        else:
            checks.append({"rule": "ordering", "pair": f"{k1}<={k2}", "ok": False})
            violations.append({"rule": "ordering", "fields": [k1, k2], "severity": "alta",
                               "detail": f"{k1} ({d1.isoformat()}) posterior a {k2} ({d2.isoformat()})"})

    if parsed["data_com"] and parsed["ex"]:
        delta = (parsed["ex"] - parsed["data_com"]).days
        if delta not in (1, 2, 3):
            violations.append({"rule": "ex_after_com", "severity": "baixa",
                               "detail": f"ex - data_com = {delta}d (esperado ~1 dia útil)"})
        else:
            checks.append({"rule": "ex_after_com", "ok": True, "detail": f"{delta}d"})

    for k, d in present:
        if not (2000 <= d.year <= 2100):
            violations.append({"rule": "year_plausible", "field": k, "severity": "media",
                               "detail": f"ano implausível: {d.year}"})

    return {"checks": checks, "violations": violations,
            "ok": len([v for v in violations if v["severity"] == "alta"]) == 0,
            "max_severity": _max_severity(violations)}


def check_value_coherence(kind, gross_value=None, net_value=None, irrf_rate=None,
                          rel_tolerance=0.01, abs_tolerance=0.0001):
    checks, violations = [], []

    if kind == "ratio":
        if gross_value or net_value:
            violations.append({"rule": "ratio_no_cash", "severity": "media",
                               "detail": "evento de proporção não deveria ter valor monetário"})
        else:
            checks.append({"rule": "ratio_no_cash", "ok": True})
        return {"checks": checks, "violations": violations, "ok": not violations,
                "max_severity": _max_severity(violations)}

    if kind == "cash_per_share":
        if gross_value is not None and net_value is not None and irrf_rate is not None:
            expected = gross_value * (1 - irrf_rate)
            tol = max(abs_tolerance, rel_tolerance * abs(expected))
            ok = abs(net_value - expected) <= tol
            checks.append({"rule": "net=gross*(1-irrf)", "ok": ok,
                           "expected_net": round(expected, 8), "got_net": net_value, "tol": tol})
            if not ok:
                violations.append({"rule": "net=gross*(1-irrf)", "severity": "alta",
                                   "detail": f"líquido {net_value} ≠ esperado {round(expected, 8)} "
                                             f"(bruto {gross_value} × (1-{irrf_rate}))"})
        else:
            checks.append({"rule": "net=gross*(1-irrf)", "ok": None,
                           "detail": "dados insuficientes (bruto/líquido/irrf)"})

    return {"checks": checks, "violations": violations,
            "ok": len([v for v in violations if v["severity"] == "alta"]) == 0,
            "max_severity": _max_severity(violations)}

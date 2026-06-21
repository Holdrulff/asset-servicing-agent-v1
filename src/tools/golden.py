from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache


def _norm(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"\b(s\.?a\.?|s/a|ltda|participacoes|cia|companhia)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


@lru_cache(maxsize=8)
def _load(golden_path: str) -> tuple:
    rows = []
    with open(golden_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({k.strip(): (v or "").strip() for k, v in row.items()})
    return tuple(rows)


def lookup_golden_record(golden_path, isin="", ticker="", cnpj="", issuer=""):
    rows = _load(golden_path)
    keys = {
        "isin": (isin or "").strip().upper(),
        "ticker": (ticker or "").strip().upper(),
        "cnpj": _digits(cnpj),
        "issuer": _norm(issuer),
    }

    def row_value(row, field):
        if field == "isin":
            return (row.get("isin", "")).upper()
        if field == "ticker":
            return (row.get("ticker", "")).upper()
        if field == "cnpj":
            return _digits(row.get("cnpj", ""))
        if field == "issuer":
            return _norm(row.get("emissor", ""))
        return ""

    matches_by_key = {}
    for field, val in keys.items():
        if not val:
            continue
        matches_by_key[field] = [i for i, r in enumerate(rows) if row_value(r, field) == val]

    provided = [f for f, v in keys.items() if v]
    if not provided:
        return {"status": "unmatched", "matched_on": [],
                "discrepancies": ["nenhum identificador fornecido"], "row": None}

    hit_rows = set()
    for idxs in matches_by_key.values():
        hit_rows.update(idxs)
    if not hit_rows:
        return {"status": "unmatched", "matched_on": [],
                "discrepancies": [f"{f}={keys[f]!r} não encontrado" for f in provided],
                "row": None}

    best = max(hit_rows, key=lambda i: sum(1 for f in provided if i in matches_by_key.get(f, [])))
    matched_on = [f for f in provided if best in matches_by_key.get(f, [])]
    discrepancies = []
    for f in provided:
        if best not in matches_by_key.get(f, []):
            discrepancies.append(f"{f}={keys[f]!r} diverge do golden ({row_value(rows[best], f)!r})")

    if set(matched_on) == set(provided):
        status = "matched"
    elif matched_on:
        status = "partial"
    else:
        status = "unmatched"

    return {
        "status": status,
        "matched_on": matched_on,
        "discrepancies": discrepancies,
        "row": dict(rows[best]) if status != "unmatched" else None,
    }

from __future__ import annotations

import json
from pathlib import Path


def write_record(record: dict, records_dir: Path) -> Path:
    records_dir.mkdir(parents=True, exist_ok=True)
    path = records_dir / f"{record['document_id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

from __future__ import annotations

from pydantic import ValidationError

from ..schema import AgentSubmission


def submit_record(payload: dict) -> dict:
    try:
        sub = AgentSubmission.model_validate(payload)
    except ValidationError as e:
        return {"ok": False, "errors": e.errors(include_url=False)}
    return {"ok": True, "submission": sub.model_dump()}

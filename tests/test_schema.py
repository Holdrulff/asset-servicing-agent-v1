import pytest
from pydantic import ValidationError

from src.schema import AgentSubmission
from src.llm.replay_data import FIXTURES


def test_valid_submission_from_fixture():
    sub = AgentSubmission.model_validate(FIXTURES["01_energetica_vale_tiete_dividendo"]["submission"])
    assert sub.event_type.normalized_code == "DIVIDENDO"
    assert sub.isin.value == "BRTIETACNOR3"


def test_missing_required_field_raises():
    bad = {k: v for k, v in FIXTURES["01_energetica_vale_tiete_dividendo"]["submission"].items() if k != "isin"}
    with pytest.raises(ValidationError):
        AgentSubmission.model_validate(bad)

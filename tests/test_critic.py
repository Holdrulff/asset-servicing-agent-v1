from src.agent.critic import _parse


def test_parse_accepts_markdown_fenced_json():
    verdict = _parse(
        '```json\n'
        '{"veredito_geral": "suspeito", "rebaixar_confianca": true, '
        '"campos": [{"campo": "isin", "concorda": false}]}\n'
        '```'
    )

    assert verdict["veredito_geral"] == "suspeito"
    assert verdict["rebaixar_confianca"] is True
    assert verdict["campos"][0]["campo"] == "isin"


def test_parse_invalid_response_returns_neutral_verdict():
    verdict = _parse("sem json aqui")

    assert verdict == {"veredito_geral": "ok", "rebaixar_confianca": False,
                       "campos": [], "parse_ok": False}


def test_parse_flags_parse_success_vs_failure():
    assert _parse("sem json aqui")["parse_ok"] is False
    assert _parse('{"veredito_geral": "ok"}')["parse_ok"] is True


def test_parse_normalizes_non_list_fields():
    verdict = _parse('{"campos": "issuer", "rebaixar_confianca": 1}')

    assert verdict["campos"] == []
    assert verdict["rebaixar_confianca"] is True

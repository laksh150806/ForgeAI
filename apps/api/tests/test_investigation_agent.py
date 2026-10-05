from app.services.investigation_agent import _confidence


def test_confidence_is_bounded() -> None:
    value = _confidence([20.0, 10.0, 5.0])
    assert 0.0 <= value <= 0.95


def test_confidence_is_zero_without_evidence() -> None:
    assert _confidence([]) == 0.0


def test_confidence_rewards_clear_lead() -> None:
    close = _confidence([20.0, 19.0])
    separated = _confidence([20.0, 5.0])
    assert separated > close

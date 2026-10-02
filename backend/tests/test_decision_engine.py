from app.services.decision_engine import (
    Decision,
    DecisionEvidence,
    make_decision,
)


def test_strong_cheaper_substitute_returns_substitute():
    evidence = DecisionEvidence(
        current_price=8.50,
        substitute_similarity=0.80,
        substitute_savings_percent=35.0,
    )

    result = make_decision(evidence)

    assert result.decision == Decision.SUBSTITUTE
    assert 0.0 < result.confidence <= 0.95
    assert "similar" in result.reason.lower()
    assert "savings" in result.reason.lower()


def test_meaningful_price_increase_returns_wait():
    evidence = DecisionEvidence(
        current_price=8.50,
        forecast_price=9.20,
        forecast_change_percent=8.2,
        forecast_confidence=0.72,
    )

    result = make_decision(evidence)

    assert result.decision == Decision.WAIT
    assert 0.0 < result.confidence <= 0.95
    assert "forecast" in result.reason.lower()


def test_non_increasing_price_returns_buy():
    evidence = DecisionEvidence(
        current_price=8.50,
        forecast_price=8.40,
        forecast_change_percent=-1.2,
        forecast_confidence=0.75,
    )

    result = make_decision(evidence)

    assert result.decision == Decision.BUY
    assert 0.0 < result.confidence <= 0.90
    assert "price" in result.reason.lower()


def test_insufficient_evidence_returns_no_action():
    evidence = DecisionEvidence(
        current_price=8.50,
    )

    result = make_decision(evidence)

    assert result.decision == Decision.NO_ACTION
    assert result.confidence == 0.0
    assert "enough reliable evidence" in result.reason.lower()


def test_invalid_price_returns_no_action():
    evidence = DecisionEvidence(
        current_price=0.0,
        forecast_change_percent=10.0,
        forecast_confidence=0.90,
    )

    result = make_decision(evidence)

    assert result.decision == Decision.NO_ACTION
    assert result.confidence == 0.0
    assert "invalid" in result.reason.lower()


def test_strong_substitute_takes_priority_over_wait():
    evidence = DecisionEvidence(
        current_price=8.50,
        forecast_price=9.50,
        forecast_change_percent=11.8,
        forecast_confidence=0.80,
        substitute_similarity=0.75,
        substitute_savings_percent=40.0,
    )

    result = make_decision(evidence)

    assert result.decision == Decision.SUBSTITUTE

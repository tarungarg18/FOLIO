from backend.app.analytics import concentration, risk_metrics


def test_volatility_and_drawdown_match_known_series():
    result = risk_metrics([100, 110, 99, 108])
    expected_returns = [0.10, -0.10, 108 / 99 - 1]
    mean = sum(expected_returns) / len(expected_returns)
    sample_variance = sum((value - mean) ** 2 for value in expected_returns) / (len(expected_returns) - 1)
    expected_volatility = sample_variance**0.5 * (252**0.5)
    assert abs(result["annualized_volatility"] - expected_volatility) < 1e-12
    assert abs(result["maximum_drawdown"] - (-0.10)) < 1e-12


def test_hhi_and_effective_holdings():
    result = concentration([50, 30, 20])
    assert result["hhi"] == 0.38
    assert abs(result["effective_holdings"] - 1 / 0.38) < 1e-12


def test_risk_is_unavailable_for_insufficient_or_invalid_history():
    assert risk_metrics([100, 101])["status"] == "insufficient_data"
    assert risk_metrics([100, 0, 101])["status"] == "insufficient_data"


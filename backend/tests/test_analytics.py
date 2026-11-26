from backend.app.analytics import concentration, health_score, insights, risk_metrics
from backend.app.main import parse_csv


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


def test_csv_preview_flags_unmatched_rows_and_invalid_quantity():
    content = "\n".join([
        "asset_type,quantity,symbol,average_cost",
        "equity,3,UNMAPPED,10",
        "equity,0,BAD,5",
        "equity,2,,7",
    ])
    result = parse_csv(content)
    assert result["requires_confirmation"] is True
    assert len(result["rows"]) == 1
    assert result["rows"][0]["status"] == "unmatched_needs_review"
    assert len(result["errors"]) == 2


def test_empty_portfolio_does_not_generate_false_coverage_insight():
    assert insights({}, {"eligible_exposure": 0, "coverage_percentage": 0, "companies": []}) == []


def test_health_score_is_not_created_without_data():
    result = health_score({"eligible_exposure": 0, "coverage_percentage": 0, "companies": []}, {"status": "insufficient_data"})
    assert result["status"] == "incomplete"
    assert result["score"] is None


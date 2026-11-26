from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import sqrt

import numpy as np
import pandas as pd
from bson.decimal128 import Decimal128

from .db import get_db

METHODOLOGY_VERSION = "1.0.0"


def number(value) -> float:
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    return float(value or 0)


def latest_price(instrument_id: str) -> dict | None:
    return get_db().prices.find_one(
        {"instrument_id": instrument_id, "close": {"$gt": 0}, "validation_status": {"$in": ["valid", None]}},
        sort=[("date", -1)],
    )


def latest_nav(scheme_code: str) -> dict | None:
    return get_db().fund_navs.find_one(
        {"scheme_code": scheme_code, "nav": {"$gt": 0}, "validation_status": {"$in": ["valid", None]}},
        sort=[("date", -1)],
    )


def portfolio_snapshot(portfolio_id: str, owner_id: str) -> dict:
    db = get_db()
    portfolio = db.portfolios.find_one({"_id": portfolio_id, "owner_id": owner_id})
    if not portfolio:
        raise KeyError("Portfolio not found")
    holdings = list(db.holdings.find({"portfolio_id": portfolio_id}))
    positions = []
    total = 0.0
    missing = []
    for holding in holdings:
        instrument_id = holding["instrument_id"]
        instrument = db.instruments.find_one({"_id": instrument_id})
        if not instrument:
            missing.append(instrument_id)
            continue
        if holding["asset_type"] == "equity":
            quote = latest_price(instrument_id)
            price = number(quote.get("close")) if quote else None
            as_of = quote.get("date") if quote else None
        else:
            quote = latest_nav(holding["scheme_code"])
            price = number(quote.get("nav")) if quote else None
            as_of = quote.get("date") if quote else None
        if price is None:
            missing.append(instrument_id)
            continue
        quantity = number(holding["quantity"])
        value = quantity * price
        total += value
        disclosure = None
        if holding["asset_type"] == "mutual_fund":
            latest_disclosure = db.fund_constituents.find_one(
                {"scheme_code": holding.get("scheme_code")}, sort=[("reporting_date", -1)]
            )
            disclosure = latest_disclosure.get("reporting_date") if latest_disclosure else None
        positions.append({
            "instrument_id": instrument_id,
            "name": instrument.get("name", instrument_id),
            "symbol": instrument.get("symbol"),
            "asset_type": holding["asset_type"],
            "sector": instrument.get("sector"),
            "scheme_code": holding.get("scheme_code"),
            "quantity": quantity,
            "unit_price": price,
            "market_value": value,
            "average_cost": number(holding.get("average_cost")),
            "as_of": as_of,
            "fund_reporting_date": disclosure,
        })
    return {"portfolio": portfolio, "positions": positions, "total_value": total, "missing": missing}


def exposure(portfolio_id: str, owner_id: str) -> dict:
    snapshot = portfolio_snapshot(portfolio_id, owner_id)
    db = get_db()
    total = snapshot["total_value"]
    direct: dict[str, float] = defaultdict(float)
    indirect: dict[str, float] = defaultdict(float)
    sources: dict[str, list] = defaultdict(list)
    eligible_total = 0.0
    mapped_total = 0.0
    unassessed_fund_value = 0.0
    for position in snapshot["positions"]:
        if position["asset_type"] == "equity":
            eligible_total += position["market_value"]
            direct[position["instrument_id"]] += position["market_value"]
            mapped_total += position["market_value"]
            continue
        if position["asset_type"] != "mutual_fund":
            continue
        constituents = list(db.fund_constituents.find({"scheme_code": position["scheme_code"]}))
        snapshot_date = max((row["reporting_date"] for row in constituents), default=None)
        latest_rows = [row for row in constituents if row["reporting_date"] == snapshot_date] if snapshot_date else []
        fund_value = position["market_value"]
        equity_rows = [row for row in latest_rows if str(row.get("asset_class", "")).strip().lower() in {"equity", "equities", "stock", "listed_equity"}]
        equity_weight = sum(max(number(row.get("weight_percentage")), 0) for row in equity_rows)
        if equity_weight <= 0:
            unassessed_fund_value += fund_value
            continue
        fund_eligible = fund_value * equity_weight / 100
        eligible_total += fund_eligible
        weight_sum = 0.0
        for row in equity_rows:
            weight = number(row.get("weight_percentage"))
            if row.get("mapped_instrument_id") and weight > 0:
                fund_exposure_value = fund_value * weight / 100
                mapped_total += fund_exposure_value
                indirect[row["mapped_instrument_id"]] += fund_exposure_value
                sources[row["mapped_instrument_id"]].append({
                    "scheme_code": position["scheme_code"],
                    "fund_name": position["name"],
                    "weight_percentage": weight,
                    "exposure_value": fund_exposure_value,
                    "reporting_date": snapshot_date,
                    "publication_date": row.get("publication_date"),
                    "source_url": row.get("source_url"),
                    "provider": row.get("provider"),
                })
                weight_sum += weight
        # Unmapped equity constituents remain in the eligible denominator.
    ids = set(direct) | set(indirect)
    companies = []
    for instrument_id in ids:
        instrument = db.instruments.find_one({"_id": instrument_id}) or {}
        direct_value = direct[instrument_id]
        indirect_value = indirect[instrument_id]
        companies.append({
            "instrument_id": instrument_id,
            "name": instrument.get("name", instrument_id),
            "symbol": instrument.get("symbol"),
            "sector": instrument.get("sector"),
            "direct_value": direct_value,
            "indirect_value": indirect_value,
            "combined_value": direct_value + indirect_value,
            "portfolio_percentage": (direct_value + indirect_value) / total * 100 if total else 0,
            "fund_sources": sources[instrument_id],
        })
    companies.sort(key=lambda item: item["combined_value"], reverse=True)
    coverage = mapped_total / eligible_total * 100 if eligible_total else 0
    return {
        "companies": companies,
        "total_portfolio_value": total,
        "eligible_exposure": eligible_total,
        "verified_mapped_eligible_exposure": mapped_total,
        "coverage_percentage": min(coverage, 100),
        "unmapped_eligible_exposure": max(eligible_total - mapped_total, 0),
        "unassessed_fund_value": unassessed_fund_value,
        "coverage_note": "Only reported equity constituents are eligible; fund value without a usable equity breakdown is reported as unassessed.",
        "methodology_version": METHODOLOGY_VERSION,
    }


def risk_metrics(values: list[float], benchmark_values: list[float] | None = None) -> dict:
    series = pd.Series(values, dtype="float64").dropna()
    if len(series) < 3 or (series <= 0).any():
        return {"status": "insufficient_data", "observations": len(series)}
    returns = series.pct_change().dropna()
    volatility = float(returns.std(ddof=1) * sqrt(252))
    drawdown = series / series.cummax() - 1
    result = {
        "status": "available",
        "observations": len(returns),
        "annualized_volatility": volatility,
        "maximum_drawdown": float(drawdown.min()),
        "methodology_version": METHODOLOGY_VERSION,
    }
    if benchmark_values is not None and len(benchmark_values) == len(values):
        paired = pd.DataFrame({"portfolio": pd.Series(values).pct_change(), "benchmark": pd.Series(benchmark_values).pct_change()}).dropna()
        if len(paired) >= 2 and float(paired["benchmark"].var(ddof=1)) > 0:
            result["beta"] = float(paired["portfolio"].cov(paired["benchmark"]) / paired["benchmark"].var(ddof=1))
            result["correlation"] = float(paired["portfolio"].corr(paired["benchmark"]))
            result["benchmark_observations"] = len(paired)
    return result


def concentration(weights: list[float]) -> dict:
    values = np.asarray(weights, dtype=float)
    if len(values) == 0 or values.sum() <= 0:
        return {"hhi": None, "effective_holdings": None}
    normalized = values / values.sum()
    hhi = float(np.square(normalized).sum())
    return {"hhi": hhi, "effective_holdings": 1 / hhi}


def insights(snapshot: dict, exposure_data: dict) -> list[dict]:
    result = []
    portfolio_dates = [position.get("as_of") for position in snapshot.get("positions", []) if position.get("as_of")]
    market_as_of = max(portfolio_dates, default=None)
    if exposure_data["eligible_exposure"] > 0 and exposure_data["coverage_percentage"] < 80:
        result.append({"id": "coverage", "severity": "medium", "title": "Some eligible exposure is not mapped", "explanation": "Look-through coverage is incomplete, so hidden company exposure may be understated.", "coverage_percentage": exposure_data["coverage_percentage"], "as_of": market_as_of, "route": "/diversification"})
    for company in exposure_data["companies"]:
        if company["portfolio_percentage"] >= 15:
            result.append({"id": f"concentration-{company['instrument_id']}", "severity": "high", "title": f"{company['name']} is a large combined exposure", "explanation": "This includes direct holdings and disclosed mutual fund exposure.", "portfolio_percentage": company["portfolio_percentage"], "evidence": company, "as_of": market_as_of, "route": "/diversification"})
    overlaps = [company for company in exposure_data["companies"] if len(company.get("fund_sources", [])) > 1]
    if overlaps:
        company = max(overlaps, key=lambda item: item["indirect_value"])
        reports = [source.get("reporting_date") for source in company["fund_sources"] if source.get("reporting_date")]
        result.append({
            "id": f"fund-overlap-{company['instrument_id']}", "severity": "low",
            "title": f"{company['name']} appears in both mutual funds",
            "explanation": f"Both dated fund disclosures include {company['name']}; the per-fund holdings and dates are shown below. This is a look-through observation, not a forecast.",
            "evidence": company, "as_of": max(reports, default=None), "route": "/diversification",
        })
    return result


PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 184, "1Y": 366, "3Y": 1096, "5Y": 1826}


def _date_key(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def historical_portfolio_series(portfolio_id: str, owner_id: str, period: str = "1Y") -> dict:
    """Fixed-current-quantity hypothetical series using consistent return-basis observations."""
    if period not in PERIOD_DAYS:
        raise ValueError("Unsupported period")
    db = get_db()
    snapshot = portfolio_snapshot(portfolio_id, owner_id)
    if not snapshot["positions"]:
        return {"status": "unavailable", "reason": "Add holdings and verified price or NAV history to view a portfolio trend.", "period": period, "observations": 0, "series": []}
    cutoff = date.today() - timedelta(days=PERIOD_DAYS[period])
    price_maps: list[dict[str, float]] = []
    source_dates: list[dict] = []
    unsupported: list[str] = []
    for position in snapshot["positions"]:
        if position["asset_type"] == "equity":
            rows = list(db.prices.find({"instrument_id": position["instrument_id"]}).sort("date", 1))
            valid = {}
            for row in rows:
                basis = str(row.get("historical_price_basis", row.get("adjustment_basis", ""))).lower()
                value = row.get("total_return_value")
                if value is None and basis in {"split_and_dividend_adjusted", "total_return"}:
                    value = row.get("adjusted_close")
                if value is None or number(value) <= 0:
                    continue
                day = _date_key(row.get("date"))
                if day >= cutoff.isoformat():
                    valid[day] = number(value)
            if not valid:
                unsupported.append(position["name"])
                continue
            price_maps.append({day: position["quantity"] * value for day, value in valid.items()})
            source_dates.append({"instrument": position["name"], "from": min(valid), "through": max(valid), "basis": "adjusted total return"})
        elif position["asset_type"] == "mutual_fund":
            rows = list(db.fund_navs.find({"scheme_code": position["scheme_code"], "nav": {"$gt": 0}}).sort("date", 1))
            valid = {_date_key(row["date"]): number(row["nav"]) for row in rows if _date_key(row["date"]) >= cutoff.isoformat()}
            if not valid:
                unsupported.append(position["name"])
                continue
            price_maps.append({day: position["quantity"] * value for day, value in valid.items()})
            source_dates.append({"instrument": position["name"], "from": min(valid), "through": max(valid), "basis": "growth NAV"})
        else:
            unsupported.append(position["name"])
    if unsupported or len(price_maps) != len(snapshot["positions"]):
        return {"status": "unavailable", "reason": "A complete history is not available for every portfolio position.", "unsupported_positions": unsupported, "period": period, "observations": 0, "series": [], "source_dates": source_dates}
    common_dates = set(price_maps[0])
    for mapping in price_maps[1:]:
        common_dates.intersection_update(mapping)
    points = []
    for day in sorted(common_dates):
        value = sum(mapping[day] for mapping in price_maps)
        if value > 0:
            points.append({"date": day, "value": value})
    if len(points) < 2:
        return {"status": "unavailable", "reason": "At least two common valid valuation dates are required.", "period": period, "observations": 0, "series": [], "source_dates": source_dates}
    initial = points[0]["value"]
    for point in points:
        point["normalized_value"] = point["value"] / initial * 100
    return {"status": "available", "period": period, "observations": len(points) - 1, "series": points, "source_dates": source_dates, "label": "Hypothetical fixed-current-holdings reconstruction", "return_basis": "Adjusted equity total-return series and growth-plan NAVs; common dates only."}


def benchmark_series(benchmark_id: str, start_date: str, end_date: str) -> list[dict]:
    rows = list(get_db().benchmark_values.find({"benchmark_id": benchmark_id}).sort("date", 1))
    values = [row for row in rows if start_date <= _date_key(row["date"]) <= end_date and str(row.get("return_type", "")).lower() in {"tri", "total_return", "price_index"} and number(row.get("index_value")) > 0]
    if not values:
        return []
    initial = number(values[0].get("index_value"))
    return [{"date": _date_key(row["date"]), "normalized_value": number(row["index_value"]) / initial * 100,
             "return_type": row.get("return_type"), "benchmark_label": row.get("benchmark_label")}
            for row in values]


def historical_risk(series: list[dict], benchmark: list[dict] | None = None) -> dict:
    if len(series) < 3:
        return {"status": "insufficient_data", "observations": max(len(series) - 1, 0)}
    frame = pd.DataFrame(series).sort_values("date").set_index("date")
    values = frame["value"].astype(float)
    returns = values.pct_change().dropna()
    drawdown = values / values.cummax() - 1
    rolling = returns.rolling(21, min_periods=15).std(ddof=1) * sqrt(252)
    result = {
        "status": "available",
        "period_start": str(values.index[0]),
        "period_end": str(values.index[-1]),
        "observations": len(returns),
        "annualized_volatility": float(returns.std(ddof=1) * sqrt(252)),
        "maximum_drawdown": float(drawdown.min()),
        "drawdown_series": [{"date": str(day), "drawdown": float(value)} for day, value in drawdown.items()],
        "rolling_volatility_series": [{"date": str(day), "volatility": float(value)} for day, value in rolling.dropna().items()],
        "methodology_version": METHODOLOGY_VERSION,
    }
    if benchmark:
        benchmark_frame = pd.DataFrame(benchmark).set_index("date").sort_index()
        combined = pd.concat([returns.rename("portfolio"), benchmark_frame["normalized_value"].pct_change().rename("benchmark")], axis=1, join="inner").dropna()
        if len(combined) >= 3 and combined["benchmark"].var(ddof=1) > 0:
            result["beta"] = float(combined["portfolio"].cov(combined["benchmark"]) / combined["benchmark"].var(ddof=1))
            result["correlation"] = float(combined["portfolio"].corr(combined["benchmark"]))
            result["benchmark_observations"] = len(combined)
            result["benchmark_period_start"] = combined.index[0]
            result["benchmark_period_end"] = combined.index[-1]
    return result


def health_score(exposure_data: dict, risk_data: dict) -> dict:
    if exposure_data["eligible_exposure"] <= 0 or risk_data.get("status") != "available":
        return {"status": "incomplete", "score": None, "components": [], "reason": "Eligible mapped exposure and valid historical risk observations are required."}
    concentration_data = concentration([item["combined_value"] for item in exposure_data["companies"]])
    hhi = concentration_data["hhi"] or 1
    coverage = exposure_data["coverage_percentage"] / 100
    # Transparent v1 heuristic; thresholds are fixed and versioned, not a validated risk model.
    components = [
        {"key": "diversification", "weight": 0.30, "score": max(0, min(100, (1 - hhi) * 125)), "formula": "(1 - HHI) × 125"},
        {"key": "concentration", "weight": 0.25, "score": max(0, min(100, (1 - hhi * 1.5) * 100)), "formula": "100 - 150 × HHI"},
        {"key": "volatility", "weight": 0.20, "score": max(0, min(100, (1 - risk_data["annualized_volatility"] / 0.6) * 100)), "formula": "100 × (1 - annualized volatility / 60%)"},
        {"key": "drawdown", "weight": 0.15, "score": max(0, min(100, (1 - abs(risk_data["maximum_drawdown"]) / 0.5) * 100)), "formula": "100 × (1 - absolute max drawdown / 50%)"},
        {"key": "coverage", "weight": 0.10, "score": coverage * 100, "formula": "Verified mapped eligible exposure / eligible exposure"},
    ]
    score = round(sum(item["score"] * item["weight"] for item in components))
    return {"status": "heuristic", "score": score, "components": components, "methodology_version": "health-v1", "disclaimer": "Internal educational heuristic; not independently validated."}

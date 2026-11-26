from collections import defaultdict
from datetime import date
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
    return get_db().prices.find_one({"instrument_id": instrument_id}, sort=[("date", -1)])


def latest_nav(scheme_code: str) -> dict | None:
    return get_db().fund_navs.find_one({"scheme_code": scheme_code}, sort=[("date", -1)])


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
        fund_eligible = position["market_value"]
        eligible_total += fund_eligible
        weight_sum = 0.0
        for row in latest_rows:
            weight = number(row.get("weight_percentage"))
            if row.get("mapped_instrument_id") and weight > 0:
                mapped_total += fund_eligible * weight / 100
                indirect[row["mapped_instrument_id"]] += fund_eligible * weight / 100
                sources[row["mapped_instrument_id"]].append({
                    "scheme_code": position["scheme_code"],
                    "fund_name": position["name"],
                    "weight_percentage": weight,
                    "reporting_date": snapshot_date,
                })
                weight_sum += weight
        # The remaining equity weight is unknown unless the disclosure reports an explicit residual row.
        if weight_sum > 100.5:
            mapped_total -= fund_eligible * (weight_sum - 100) / 100
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
    if exposure_data["coverage_percentage"] < 80:
        result.append({"id": "coverage", "severity": "medium", "title": "Some eligible exposure is not mapped", "explanation": "Look-through coverage is incomplete, so hidden company exposure may be understated.", "coverage_percentage": exposure_data["coverage_percentage"], "as_of": date.today().isoformat(), "route": "/diversification"})
    for company in exposure_data["companies"]:
        if company["portfolio_percentage"] >= 15:
            result.append({"id": f"concentration-{company['instrument_id']}", "severity": "high", "title": f"{company['name']} is a large combined exposure", "explanation": "This includes direct holdings and disclosed mutual fund exposure.", "portfolio_percentage": company["portfolio_percentage"], "evidence": company, "as_of": date.today().isoformat(), "route": "/diversification"})
    return result

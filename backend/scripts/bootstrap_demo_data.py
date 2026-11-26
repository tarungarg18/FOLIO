"""Download real source data and seed FOLIO's illustrative demo portfolio.

Investor positions are sample quantities. Security prices, fund NAVs, fund
disclosures and index values are collected from their named providers at run
time; no downloaded financial history is checked into the repository.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import openpyxl
from pymongo import UpdateOne

from app.db import close, connect, get_db
from app.security import hash_password

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "data" / "demo"
RAW_DIR = ROOT / "data" / "raw" / "demo"
RAW_DIR.mkdir(parents=True, exist_ok=True)

YAHOO_CHART = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
MFAPI_HISTORY = "https://api.mfapi.in/mf/{scheme_code}"
AMFI_LATEST_NAV = "https://portal.amfiindia.com/spages/NAVAll.txt"
NIFTY_REFERER = "https://finance.yahoo.com/"
FUNDS = {
    "122639": {
        "name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        "amc": "PPFAS Mutual Fund",
        "reporting_date": "2026-09-30",
        "url": "https://amc.ppfas.com/downloads/portfolio-disclosure/2026/PPFCF_PPFAS_Monthly_Portfolio_Report_September_30_2026.xlsx",
        "workbook": "ppfas_flexicap_2026-09.xlsx",
        "sheet": "PPFCF",
        "layout": "ppfas",
    },
    "119718": {
        "name": "SBI Flexicap Fund - Direct Plan - Growth",
        "amc": "SBI Mutual Fund",
        "reporting_date": "2026-10-31",
        "url": "https://www.sbimf.com/docs/default-source/scheme-portfolios/all-schemes-monthly-portfolio---as-on-31st-october-2026.xlsx",
        "workbook": "sbi_all_schemes_2026-10.xlsx",
        "sheet": "SFLEXI",
        "layout": "sbi",
    },
}


def request_bytes(client: httpx.Client, url: str, *, retries: int = 4, **kwargs) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.get(url, **kwargs)
            response.raise_for_status()
            return response.content
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not retrieve {url}: {last_error}")


def save_raw(filename: str, content: bytes) -> str:
    path = RAW_DIR / filename
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def ingest_prices(client: httpx.Client, instruments: list[dict], db) -> int:
    inserted = 0
    now = datetime.now(timezone.utc)
    period_end = int(now.timestamp())
    period_start = int((now - timedelta(days=5 * 365 + 2)).timestamp())
    for instrument in instruments:
        symbol = instrument["symbol"]
        url = YAHOO_CHART.format(symbol=symbol)
        response = client.get(
            url,
            params={"period1": period_start, "period2": period_end, "interval": "1d", "events": "div,splits"},
        )
        response.raise_for_status()
        content = response.content
        checksum = save_raw(f"yahoo_{symbol.replace('.', '_')}_5y.json", content)
        payload = response.json()["chart"]
        if payload.get("error") or not payload.get("result"):
            raise RuntimeError(f"Yahoo Finance returned no history for {symbol}: {payload.get('error')}")
        result = payload["result"][0]
        quote = result["indicators"]["quote"][0]
        adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
        timestamps = result.get("timestamp", [])
        rows = []
        for index, timestamp in enumerate(timestamps):
            close_value = quote.get("close", [])[index]
            adjusted_value = adjusted[index] if index < len(adjusted) else None
            if close_value is None or adjusted_value is None or close_value <= 0 or adjusted_value <= 0:
                continue
            day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
            rows.append({
                "instrument_id": instrument["instrument_id"], "date": day,
                "open": quote.get("open", [])[index], "high": quote.get("high", [])[index],
                "low": quote.get("low", [])[index], "close": close_value,
                "adjusted_close": adjusted_value, "volume": quote.get("volume", [])[index],
                "historical_price_basis": "split_and_dividend_adjusted",
                "adjustment_basis": "split_and_dividend_adjusted", "currency": "INR",
                "provider": "Yahoo Finance chart endpoint (unofficial)", "source_url": url,
                "retrieved_at": now, "validation_status": "valid",
            })
        if len(rows) < 500:
            raise RuntimeError(f"Only {len(rows)} daily records were retrieved for {symbol}; expected around five years.")
        db.prices.bulk_write([
            UpdateOne({"instrument_id": row["instrument_id"], "date": row["date"]}, {"$set": row}, upsert=True)
            for row in rows
        ], ordered=False)
        inserted += len(rows)
        db.data_manifests.insert_one({
            "dataset": f"equity_prices_{symbol}", "provider": "Yahoo Finance chart endpoint (unofficial)",
            "source_url": url, "retrieved_at": now, "data_period": {"from": rows[0]["date"], "through": rows[-1]["date"]},
            "record_count": len(rows), "adjustment_methodology": "Yahoo adjusted close; dividend and split adjusted",
            "currency": "INR", "usage_status": "research_only_check_current_yahoo_terms",
            "checksum_sha256": checksum, "validation_status": "valid",
        })
        time.sleep(0.35)
    return inserted


def ingest_navs(client: httpx.Client, db) -> int:
    now = datetime.now(timezone.utc)
    # The official AMFI file is used to verify scheme identities and current NAVs.
    latest_content = request_bytes(client, AMFI_LATEST_NAV)
    save_raw("amfi_latest_nav.txt", latest_content)
    latest_rows = {}
    for line in latest_content.decode("utf-8-sig", "replace").splitlines():
        fields = line.split(";")
        if len(fields) >= 8 and fields[0].strip() in FUNDS:
            latest_rows[fields[0].strip()] = fields
    if set(latest_rows) != set(FUNDS):
        raise RuntimeError(f"AMFI latest NAV did not contain all expected scheme codes: {sorted(set(FUNDS) - set(latest_rows))}")

    total = 0
    for scheme_code, fund in FUNDS.items():
        url = MFAPI_HISTORY.format(scheme_code=scheme_code)
        content = request_bytes(client, url)
        checksum = save_raw(f"mfapi_nav_{scheme_code}.json", content)
        payload = json.loads(content)
        actual_code = str(payload.get("meta", {}).get("scheme_code", ""))
        if actual_code != scheme_code:
            raise RuntimeError(f"NAV scheme mismatch: requested {scheme_code}, received {actual_code}")
        nav_rows = []
        for item in payload.get("data", []):
            try:
                day = datetime.strptime(item["date"], "%d-%m-%Y").date().isoformat()
                nav = float(item["nav"])
            except (KeyError, ValueError, TypeError):
                continue
            if nav > 0 and day >= (date.today() - timedelta(days=5 * 365 + 2)).isoformat():
                nav_rows.append({
                    "scheme_code": scheme_code, "date": day, "nav": nav, "currency": "INR",
                    "provider": "MFAPI mirror of AMFI NAV history", "source_url": url,
                    "retrieved_at": now, "validation_status": "valid",
                })
        nav_rows.sort(key=lambda row: row["date"])
        official_latest_date = datetime.strptime(latest_rows[scheme_code][7].strip(), "%d-%b-%Y").date().isoformat()
        official_latest_nav = float(latest_rows[scheme_code][6].strip())
        matching_latest = next((row for row in reversed(nav_rows) if row["date"] == official_latest_date), None)
        if not matching_latest or abs(matching_latest["nav"] - official_latest_nav) > 0.00011:
            raise RuntimeError(f"MFAPI NAV series for {scheme_code} did not reconcile to AMFI latest NAV on {official_latest_date}")
        db.fund_navs.bulk_write([
            UpdateOne({"scheme_code": row["scheme_code"], "date": row["date"]}, {"$set": row}, upsert=True)
            for row in nav_rows
        ], ordered=False)
        db.fund_schemes.update_one({"scheme_code": scheme_code}, {"$set": {
            "scheme_code": scheme_code, "scheme_name": fund["name"], "amc": fund["amc"],
            "plan": "Direct", "option": "Growth", "nav_source": url,
            "identity_verified_against_amfi": True,
        }}, upsert=True)
        db.instruments.update_one({"_id": scheme_code}, {"$set": {
            "name": fund["name"], "symbol": scheme_code,
            "asset_type": "mutual_fund", "scheme_code": scheme_code,
        }}, upsert=True)
        db.data_manifests.insert_one({
            "dataset": f"fund_navs_{scheme_code}", "provider": "MFAPI mirror of AMFI; latest NAV cross-checked against official AMFI",
            "source_url": url, "official_latest_source_url": AMFI_LATEST_NAV, "retrieved_at": now,
            "data_period": {"from": nav_rows[0]["date"], "through": nav_rows[-1]["date"]},
            "record_count": len(nav_rows), "currency": "INR", "usage_status": "verify_mfapi_terms_before_redistribution",
            "checksum_sha256": checksum, "validation_status": "valid",
            "amfi_latest_reconciled": {"date": official_latest_date, "nav": official_latest_nav},
        })
        total += len(nav_rows)
    return total


def _parse_percent(value, fractional: bool) -> float | None:
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    if result < 0:
        return None
    return result * 100 if fractional else result


def read_fund_holdings(client: httpx.Client, fund: dict) -> tuple[list[dict], str]:
    content = request_bytes(client, fund["url"])
    checksum = save_raw(fund["workbook"], content)
    book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = book[fund["sheet"]]
    header_row = next((i for i, row in enumerate(sheet.iter_rows(values_only=True)) if any("ISIN" in str(cell or "").upper() for cell in row)), None)
    if header_row is None:
        raise RuntimeError(f"Could not find an ISIN header in {fund['workbook']}")
    rows = []
    active_class = ""
    for row in sheet.iter_rows(min_row=header_row + 2, values_only=True):
        cells = [str(value).strip() if value is not None else "" for value in row]
        joined = " ".join(cells[:5]).lower()
        if "equity & equity related" in joined or "equity shares" in joined:
            active_class = "equity"
        elif any(term in joined for term in ["debt instruments", "money market", "cash & cash equivalents", "treps", "government securities", "corporate debt"]):
            active_class = "debt"
        if active_class != "equity":
            continue
        if fund["layout"] == "ppfas":
            name, isin, sector, raw_weight = row[1], row[2], row[3], row[6]
            weight = _parse_percent(raw_weight, fractional=True)
        else:
            name, isin, sector, raw_weight = row[2], row[3], row[4], row[7]
            weight = _parse_percent(raw_weight, fractional=False)
        security_isin = str(isin or "").strip().upper()
        security_name = str(name or "").strip()
        sector_name = str(sector or "").strip()
        if not security_isin.startswith("IN") or not security_name or not weight:
            continue
        rows.append({
            "security_isin": security_isin, "security_name": security_name,
            "sector": sector_name, "asset_class": "equity", "weight_percentage": weight,
        })
    book.close()
    if not rows:
        raise RuntimeError(f"No equity holdings were parsed from {fund['workbook']}")
    return rows, checksum


def ingest_disclosures(client: httpx.Client, db) -> int:
    now = datetime.now(timezone.utc)
    total = 0
    for scheme_code, fund in FUNDS.items():
        constituents, checksum = read_fund_holdings(client, fund)
        reporting_date = fund["reporting_date"]
        for row in constituents:
            instrument_id = row["security_isin"]
            db.instruments.update_one({"_id": instrument_id}, {"$setOnInsert": {
                "_id": instrument_id, "isin": instrument_id, "name": row["security_name"],
                "sector": row["sector"], "asset_type": "equity",
            }}, upsert=True)
            instrument = db.instruments.find_one({"_id": instrument_id}) or {}
            row.update({
                "scheme_code": scheme_code, "reporting_date": reporting_date,
                # Publication timing is not provided consistently in the workbook; do not substitute retrieval date.
                "publication_date": fund.get("publication_date"), "mapped_instrument_id": instrument_id,
                "source_url": fund["url"], "provider": fund["amc"],
                "retrieved_at": now, "currency": "INR", "validation_status": "valid",
            })
            # Do not overwrite a direct-security symbol/sector with disclosure labels.
            if not instrument.get("symbol"):
                db.instruments.update_one({"_id": instrument_id}, {"$set": {"sector": row["sector"]}})
        db.fund_constituents.bulk_write([
            UpdateOne({"scheme_code": scheme_code, "reporting_date": reporting_date, "security_isin": row["security_isin"]}, {"$set": row}, upsert=True)
            for row in constituents
        ], ordered=False)
        db.data_manifests.insert_one({
            "dataset": f"fund_constituents_{scheme_code}", "provider": fund["amc"],
            "source_url": fund["url"], "retrieved_at": now,
            "data_period": {"reporting_date": reporting_date}, "record_count": len(constituents),
            "usage_status": "public_monthly_disclosure_review_source_terms_before_redistribution",
            "checksum_sha256": checksum, "validation_status": "valid",
        })
        total += len(constituents)
    return total


def ingest_benchmarks(client: httpx.Client, db) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    period_end = int(now.timestamp())
    period_start = int((now - timedelta(days=5 * 365 + 2)).timestamp())
    for benchmark_id, symbol, label in [
        ("nifty_50_price", "%5ENSEI", "NIFTY 50 price index"),
        ("nifty_500_price", "%5ECRSLDX", "NIFTY 500 price index"),
    ]:
        url = YAHOO_CHART.format(symbol=symbol)
        response = client.get(url, params={"period1": period_start, "period2": period_end, "interval": "1d"})
        response.raise_for_status()
        content = response.content
        checksum = save_raw(f"yahoo_{benchmark_id}_5y.json", content)
        chart = response.json()["chart"]
        if chart.get("error") or not chart.get("result"):
            raise RuntimeError(f"Yahoo Finance returned no history for {label}: {chart.get('error')}")
        result = chart["result"][0]
        timestamps = result.get("timestamp", [])
        closes = result["indicators"]["quote"][0].get("close", [])
        collected = {
            datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(): float(value)
            for timestamp, value in zip(timestamps, closes) if value is not None and value > 0
        }
        if len(collected) < 500:
            raise RuntimeError(f"Yahoo Finance returned only {len(collected)} observations for {label}.")
        sorted_rows = [{
            "benchmark_id": benchmark_id, "date": day, "index_value": collected[day],
            "return_type": "price_index", "benchmark_label": label,
            "provider": "Yahoo Finance chart endpoint (unofficial)", "source_url": url,
            "retrieved_at": now, "validation_status": "valid", "currency": "INR",
        } for day in sorted(collected)]
        db.benchmark_values.bulk_write([
            UpdateOne({"benchmark_id": row["benchmark_id"], "date": row["date"]}, {"$set": row}, upsert=True)
            for row in sorted_rows
        ], ordered=False)
        db.data_manifests.insert_one({
            "dataset": benchmark_id, "provider": "Yahoo Finance chart endpoint (unofficial)", "source_url": url,
            "retrieved_at": now, "data_period": {"from": sorted_rows[0]["date"], "through": sorted_rows[-1]["date"]},
            "record_count": len(sorted_rows), "usage_status": "research_only_check_current_yahoo_terms",
            "return_type": "price_index_dividends_excluded", "checksum_sha256": checksum, "validation_status": "valid",
        })
        count += len(sorted_rows)
    return count


def seed_instruments_and_positions(db) -> tuple[str, str]:
    with (DEMO_DIR / "instrument_master.csv").open(newline="", encoding="utf-8-sig") as handle:
        instruments = list(csv.DictReader(handle))
    for item in instruments:
        db.instruments.update_one({"_id": item["instrument_id"]}, {"$set": {
            "isin": item["isin"], "symbol": item["symbol"],
            "name": item["name"], "sector": item["sector"], "asset_type": "equity",
            "provider": "NSE security master mapping; ticker verified against Yahoo Finance chart metadata",
        }}, upsert=True)

    email = "demo@folio.local"
    user = db.users.find_one({"email": email})
    if not user:
        user_id = str(uuid.uuid4())
        user = {"_id": user_id, "email": email, "name": "Demo Investor", "password_hash": hash_password(secrets.token_urlsafe(32)), "created_at": datetime.now(timezone.utc)}
        db.users.insert_one(user)
    else:
        user_id = user["_id"]
    portfolio = db.portfolios.find_one({"owner_id": user_id, "slug": "illustrative"})
    if not portfolio:
        portfolio_id = str(uuid.uuid4())
        portfolio = {"_id": portfolio_id, "owner_id": user_id, "slug": "illustrative", "name": "Illustrative Investor Portfolio", "is_illustrative": True, "created_at": datetime.now(timezone.utc)}
        db.portfolios.insert_one(portfolio)
    else:
        portfolio_id = portfolio["_id"]
    with (DEMO_DIR / "sample_portfolio.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    by_symbol = {item["symbol"]: item for item in instruments}
    for row in rows:
        scheme_code = row.get("scheme_code") or None
        instrument_id = (by_symbol[row["symbol"]]["instrument_id"] if row.get("symbol") else scheme_code)
        db.holdings.update_one(
            {"portfolio_id": portfolio_id, "instrument_id": instrument_id},
            {"$set": {"portfolio_id": portfolio_id, "instrument_id": instrument_id,
                       "asset_type": row["asset_type"], "quantity": float(row["quantity"]),
                       "average_cost": float(row.get("average_cost") or 0), "scheme_code": scheme_code,
                       "sample_position": True}}, upsert=True,
        )
    return user_id, portfolio_id


def main() -> None:
    client = httpx.Client(timeout=httpx.Timeout(45.0), headers={"User-Agent": "FOLIO educational POC data bootstrap"})
    connect()
    db = get_db()
    try:
        user_id, portfolio_id = seed_instruments_and_positions(db)
        instruments = list(csv.DictReader((DEMO_DIR / "instrument_master.csv").open(encoding="utf-8-sig", newline="")))
        prices = ingest_prices(client, instruments, db)
        navs = ingest_navs(client, db)
        constituents = ingest_disclosures(client, db)
        benchmarks = ingest_benchmarks(client, db)
        db.data_manifests.insert_one({
            "dataset": "folio_demo_bootstrap", "provider": "FOLIO bootstrap script",
            "retrieved_at": datetime.now(timezone.utc), "portfolio_id": portfolio_id,
            "user_id": user_id, "status": "complete", "sample_positions": 7,
            "price_records": prices, "nav_records": navs,
            "fund_constituent_records": constituents, "benchmark_records": benchmarks,
            "label": "Illustrative quantities; market observations from cited providers",
        })
        print(f"Demo portfolio ready: 5 equities, 2 funds; {prices:,} prices, {navs:,} NAVs, {constituents:,} disclosed constituents, {benchmarks:,} benchmark values.")
        print("Investor quantities are illustrative. Check source usage terms before redistribution.")
    finally:
        client.close()
        close()


if __name__ == "__main__":
    main()

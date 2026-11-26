import csv
import io
import logging
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from bson import ObjectId
from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .analytics import benchmark_series, exposure, health_score, historical_portfolio_series, historical_risk, insights, portfolio_snapshot
from .config import settings
from .db import close, connect, get_db
from .schemas import CopilotRequest, CsvConfirmation, HoldingInput, LoginRequest, RegisterRequest
from .security import hash_password, issue_session, user_for_token, verify_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("folio")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        connect()
    except Exception as exc:
        logger.warning("MongoDB unavailable at startup: %s", exc)
    yield
    close()


app = FastAPI(title="FOLIO API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error id=%s", request_id)
        response = JSONResponse(status_code=500, content={"error": {"code": "internal_error", "request_id": request_id}})
    response.headers["x-request-id"] = request_id
    return response


def current_user(folio_session: str | None = Cookie(default=None)) -> dict:
    if not folio_session:
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    user = user_for_token(folio_session)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "invalid_session"})
    return user


def jsonable(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items() if key != "password_hash"}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    return value


def require_portfolio(portfolio_id: str, owner_id: str) -> dict:
    portfolio = get_db().portfolios.find_one({"_id": portfolio_id, "owner_id": owner_id})
    if not portfolio:
        raise HTTPException(status_code=404, detail={"code": "portfolio_not_found"})
    return portfolio


@app.get("/health")
def health():
    try:
        get_db().command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})


@app.post("/api/v1/auth/register", status_code=201)
def register(payload: RegisterRequest):
    db = get_db()
    email = payload.email.lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail={"code": "email_exists"})
    user_id = str(uuid.uuid4())
    db.users.insert_one({"_id": user_id, "email": email, "name": payload.name, "password_hash": hash_password(payload.password), "created_at": datetime.now(timezone.utc)})
    portfolio_id = str(uuid.uuid4())
    db.portfolios.insert_one({"_id": portfolio_id, "owner_id": user_id, "slug": "main", "name": "My Portfolio", "created_at": datetime.now(timezone.utc)})
    return {"user": {"id": user_id, "email": email, "name": payload.name}}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, response: Response):
    user = get_db().users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail={"code": "invalid_credentials"})
    token = issue_session(user["_id"])
    response.set_cookie("folio_session", token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_days * 86400, path="/")
    return {"user": {"id": user["_id"], "email": user["email"], "name": user["name"]}}


@app.post("/api/v1/auth/logout")
def logout(response: Response, folio_session: str | None = Cookie(default=None)):
    if folio_session:
        import hashlib
        get_db().sessions.delete_one({"token_hash": hashlib.sha256(folio_session.encode()).hexdigest()})
    response.delete_cookie("folio_session", path="/")
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(user=Depends(current_user)):
    return {"user": {"id": user["_id"], "email": user["email"], "name": user["name"]}}


@app.post("/api/v1/demo/open")
def open_demo(response: Response):
    db = get_db()
    email = "demo@folio.local"
    user = db.users.find_one({"email": email})
    if not user:
        user_id = str(uuid.uuid4())
        user = {"_id": user_id, "email": email, "name": "Demo Investor", "password_hash": hash_password(secrets.token_urlsafe(32)), "created_at": datetime.now(timezone.utc)}
        db.users.insert_one(user)
        portfolio_id = str(uuid.uuid4())
        db.portfolios.insert_one({"_id": portfolio_id, "owner_id": user_id, "slug": "illustrative", "name": "Illustrative Investor Portfolio", "is_illustrative": True, "created_at": datetime.now(timezone.utc)})
        db.data_manifests.insert_one({"dataset": "demo_positions", "status": "synthetic_positions_real_market_data_required", "label": "Illustrative positions; market data must be sourced and traceable"})
    token = issue_session(user["_id"])
    response.set_cookie("folio_session", token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_days * 86400, path="/")
    portfolio = db.portfolios.find_one({"owner_id": user["_id"]})
    return {"user": {"id": user["_id"], "email": email, "name": user["name"]}, "portfolio": jsonable(portfolio)}


@app.get("/api/v1/portfolios")
def list_portfolios(user=Depends(current_user)):
    return {"data": [jsonable(item) for item in get_db().portfolios.find({"owner_id": user["_id"]})]}


@app.get("/api/v1/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str, user=Depends(current_user)):
    return jsonable(require_portfolio(portfolio_id, user["_id"]))


@app.get("/api/v1/portfolios/{portfolio_id}/holdings")
def get_holdings(portfolio_id: str, user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    return {"data": [jsonable(item) for item in get_db().holdings.find({"portfolio_id": portfolio_id})]}


@app.post("/api/v1/portfolios/{portfolio_id}/holdings", status_code=201)
def add_holding(portfolio_id: str, payload: HoldingInput, user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    if payload.asset_type not in {"equity", "mutual_fund", "cash", "debt"}:
        raise HTTPException(status_code=422, detail={"code": "invalid_asset_type"})
    if payload.asset_type == "mutual_fund" and not payload.scheme_code:
        raise HTTPException(status_code=422, detail={"code": "scheme_code_required"})
    doc = payload.model_dump()
    doc.update({"_id": str(uuid.uuid4()), "portfolio_id": portfolio_id})
    get_db().holdings.update_one({"portfolio_id": portfolio_id, "instrument_id": payload.instrument_id}, {"$set": doc}, upsert=True)
    return jsonable(doc)


@app.put("/api/v1/holdings/{holding_id}")
def update_holding(holding_id: str, payload: HoldingInput, user=Depends(current_user)):
    db = get_db()
    holding = db.holdings.find_one({"_id": holding_id})
    if not holding:
        raise HTTPException(status_code=404, detail={"code": "holding_not_found"})
    require_portfolio(holding["portfolio_id"], user["_id"])
    db.holdings.update_one({"_id": holding_id}, {"$set": payload.model_dump()})
    return jsonable({**holding, **payload.model_dump()})


@app.delete("/api/v1/holdings/{holding_id}")
def delete_holding(holding_id: str, user=Depends(current_user)):
    db = get_db()
    holding = db.holdings.find_one({"_id": holding_id})
    if not holding:
        raise HTTPException(status_code=404, detail={"code": "holding_not_found"})
    require_portfolio(holding["portfolio_id"], user["_id"])
    db.holdings.delete_one({"_id": holding_id})
    return {"ok": True}


def parse_csv(content: str) -> dict:
    reader = csv.DictReader(io.StringIO(content))
    required = {"asset_type", "quantity"}
    headers = {header.strip().lower() for header in (reader.fieldnames or [])}
    if not required.issubset(headers) or not ({"symbol", "isin", "scheme_code"} & headers):
        raise HTTPException(status_code=422, detail={"code": "invalid_csv_headers", "required": ["asset_type", "quantity", "symbol or isin or scheme_code"]})
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail={"code": "empty_csv"})
    rows, errors, seen = [], [], set()
    for line_number, row in enumerate(reader, start=2):
        normalized = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        identifier = normalized.get("isin") or normalized.get("scheme_code") or normalized.get("symbol")
        try:
            if not identifier:
                raise ValueError("security identifier is required")
            quantity = float(normalized.get("quantity", ""))
            if quantity <= 0:
                raise ValueError("quantity must be positive")
            asset_type = normalized.get("asset_type", "").lower()
            if asset_type not in {"equity", "mutual_fund", "cash", "debt"}:
                raise ValueError("unsupported asset_type")
            key = (identifier, asset_type)
            if key in seen:
                raise ValueError("duplicate row")
            seen.add(key)
            rows.append({"line": line_number, "identifier": identifier, "isin": normalized.get("isin"), "symbol": normalized.get("symbol"), "scheme_code": normalized.get("scheme_code"), "asset_type": asset_type, "quantity": quantity, "average_cost": float(normalized.get("average_cost") or 0), "status": "unmatched_needs_review"})
        except (TypeError, ValueError) as exc:
            errors.append({"line": line_number, "error": str(exc)})
    return {"rows": rows, "errors": errors, "requires_confirmation": True}


@app.post("/api/v1/portfolios/{portfolio_id}/import/preview")
async def import_preview(portfolio_id: str, file: UploadFile = File(...), user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail={"code": "csv_required"})
    content = await file.read(2_000_001)
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail={"code": "file_too_large"})
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail={"code": "csv_encoding_invalid"}) from exc
    return parse_csv(decoded)


@app.post("/api/v1/portfolios/{portfolio_id}/import/confirm", status_code=201)
def import_confirm(portfolio_id: str, payload: CsvConfirmation, user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    db = get_db()
    instruments = {item["_id"] for item in db.instruments.find({}, {"_id": 1})}
    unresolved = [row.instrument_id for row in payload.rows if row.instrument_id not in instruments]
    if unresolved:
        raise HTTPException(status_code=422, detail={"code": "unresolved_instruments", "identifiers": unresolved})
    docs = []
    for row in payload.rows:
        doc = row.model_dump()
        doc.update({"_id": str(uuid.uuid4()), "portfolio_id": portfolio_id})
        docs.append(doc)
    for doc in docs:
        db.holdings.update_one({"portfolio_id": portfolio_id, "instrument_id": doc["instrument_id"]}, {"$set": doc}, upsert=True)
    return {"imported": len(docs)}


@app.get("/api/v1/market/instruments")
def search_instruments(q: str, user=Depends(current_user)):
    del user
    regex = {"$regex": q, "$options": "i"}
    items = get_db().instruments.find({"$or": [{"symbol": regex}, {"name": regex}, {"isin": regex}]}, limit=25)
    return {"data": [jsonable(item) for item in items]}


@app.get("/api/v1/market/data-health")
def data_health(user=Depends(current_user)):
    del user
    return {"data": [jsonable(row) for row in get_db().data_manifests.find().sort("retrieved_at", -1).limit(30)]}


@app.get("/api/v1/analytics/summary")
def analytics_summary(portfolio_id: str, user=Depends(current_user)):
    snapshot = portfolio_snapshot(portfolio_id, user["_id"])
    exposure_data = exposure(portfolio_id, user["_id"])
    totals_by_type = {}
    for row in snapshot["positions"]:
        totals_by_type[row["asset_type"]] = totals_by_type.get(row["asset_type"], 0) + row["market_value"]
    return {"data": {"name": snapshot["portfolio"]["name"], "is_illustrative": snapshot["portfolio"].get("is_illustrative", False), "total_value": snapshot["total_value"], "positions": snapshot["positions"], "asset_allocation": totals_by_type, "exposure_coverage": exposure_data["coverage_percentage"], "missing_data": snapshot["missing"], "as_of": max((position["as_of"] for position in snapshot["positions"] if position["as_of"]), default=None), "methodology_version": "1.0.0"}}


@app.get("/api/v1/analytics/exposure")
def analytics_exposure(portfolio_id: str, user=Depends(current_user)):
    return {"data": exposure(portfolio_id, user["_id"])}


@app.get("/api/v1/analytics/allocation")
def analytics_allocation(portfolio_id: str, user=Depends(current_user)):
    snapshot = portfolio_snapshot(portfolio_id, user["_id"])
    lookthrough = exposure(portfolio_id, user["_id"])
    totals = {}
    for row in snapshot["positions"]:
        totals[row["asset_type"]] = totals.get(row["asset_type"], 0) + row["market_value"]
    sectors = {}
    for company in lookthrough["companies"]:
        sector = company.get("sector") or "Unclassified equity"
        sectors[sector] = sectors.get(sector, 0) + company["combined_value"]
    return {"data": {"asset_allocation": totals, "sector_allocation": sectors, "total_value": snapshot["total_value"], "eligible_exposure": lookthrough["eligible_exposure"], "mapped_exposure": lookthrough["verified_mapped_eligible_exposure"], "unmapped_exposure": lookthrough["unmapped_eligible_exposure"], "unassessed_fund_value": lookthrough.get("unassessed_fund_value", 0)}}


@app.get("/api/v1/analytics/history")
def analytics_history(portfolio_id: str, period: str = "1Y", user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    try:
        return {"data": historical_portfolio_series(portfolio_id, user["_id"], period)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_period"}) from exc


@app.get("/api/v1/analytics/risk")
def analytics_risk(portfolio_id: str, period: str = "1Y", benchmark_id: str = "nifty_50_tri", user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    try:
        history = historical_portfolio_series(portfolio_id, user["_id"], period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_period"}) from exc
    if history["status"] != "available":
        return {"data": {**history, "risk": {"status": "unavailable"}, "health": {"status": "incomplete", "score": None}}}
    benchmark = benchmark_series(benchmark_id, history["series"][0]["date"], history["series"][-1]["date"])
    risk = historical_risk(history["series"], benchmark)
    exposure_data = exposure(portfolio_id, user["_id"])
    return {"data": {**history, "risk": risk, "health": health_score(exposure_data, risk)}}


@app.get("/api/v1/analytics/overlap")
def analytics_overlap(portfolio_id: str, user=Depends(current_user)):
    result = exposure(portfolio_id, user["_id"])
    return {"data": [row for row in result["companies"] if len(row["fund_sources"]) > 1]}


@app.get("/api/v1/analytics/overlap-matrix")
def analytics_overlap_matrix(portfolio_id: str, user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    db = get_db()
    holdings = list(db.holdings.find({"portfolio_id": portfolio_id, "asset_type": "mutual_fund"}))
    schemes = []
    constituents_by_scheme = {}
    for holding in holdings:
        scheme_code = holding.get("scheme_code")
        if not scheme_code:
            continue
        rows = list(db.fund_constituents.find({"scheme_code": scheme_code}).sort("reporting_date", -1))
        if not rows:
            continue
        report_date = rows[0]["reporting_date"]
        latest = [row for row in rows if row["reporting_date"] == report_date]
        weights = {row.get("mapped_instrument_id"): float(row.get("weight_percentage", 0)) for row in latest if row.get("mapped_instrument_id") and row.get("asset_class", "").lower() in {"equity", "equities", "stock", "listed_equity"}}
        scheme = db.fund_schemes.find_one({"scheme_code": scheme_code}) or {}
        schemes.append({"scheme_code": scheme_code, "name": scheme.get("scheme_name", holding.get("instrument_id", scheme_code)), "reporting_date": report_date})
        constituents_by_scheme[scheme_code] = weights
    matrix = []
    for first in schemes:
        row = {"scheme_code": first["scheme_code"], "name": first["name"], "reporting_date": first["reporting_date"], "values": {}}
        for second in schemes:
            a, b = constituents_by_scheme[first["scheme_code"]], constituents_by_scheme[second["scheme_code"]]
            row["values"][second["scheme_code"]] = sum(min(a.get(key, 0), b.get(key, 0)) for key in set(a) & set(b))
        matrix.append(row)
    return {"data": {"schemes": schemes, "matrix": matrix, "unit": "percentage points of scheme weight", "status": "available" if schemes else "unavailable"}}


@app.get("/api/v1/analytics/benchmark")
def analytics_benchmark(portfolio_id: str, benchmark_id: str = "nifty_50_tri", period: str = "1Y", user=Depends(current_user)):
    require_portfolio(portfolio_id, user["_id"])
    try:
        history = historical_portfolio_series(portfolio_id, user["_id"], period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_period"}) from exc
    if history["status"] != "available":
        return {"data": {"status": "unavailable", "benchmark_id": benchmark_id, "period": period, "reason": history["reason"], "observations": 0}}
    benchmark = benchmark_series(benchmark_id, history["series"][0]["date"], history["series"][-1]["date"])
    portfolio_points = {point["date"]: point for point in history["series"]}
    benchmark_points = {point["date"]: point for point in benchmark}
    common_dates = sorted(set(portfolio_points) & set(benchmark_points))
    if len(common_dates) < 2:
        return {"data": {"status": "unavailable", "benchmark_id": benchmark_id, "period": period, "reason": "Insufficient common dates between the portfolio and TRI series.", "observations": max(len(common_dates)-1, 0)}}
    start = common_dates[0]
    portfolio_start = portfolio_points[start]["value"]
    benchmark_start = benchmark_points[start]["normalized_value"]
    points = [{"date": day, "portfolio": portfolio_points[day]["value"] / portfolio_start * 100, "benchmark": benchmark_points[day]["normalized_value"] / benchmark_start * 100} for day in common_dates]
    return {"data": {"status": "available", "benchmark_id": benchmark_id, "period": period, "start_date": common_dates[0], "end_date": common_dates[-1], "observations": len(points)-1, "relative_return_percentage_points": points[-1]["portfolio"]-points[-1]["benchmark"], "portfolio_label": history["label"], "series": points}}


@app.get("/api/v1/insights")
def list_insights(portfolio_id: str, user=Depends(current_user)):
    snapshot = portfolio_snapshot(portfolio_id, user["_id"])
    exposure_data = exposure(portfolio_id, user["_id"])
    return {"data": insights(snapshot, exposure_data)}


@app.get("/api/v1/insights/{insight_id}")
def get_insight(insight_id: str, portfolio_id: str, user=Depends(current_user)):
    results = list_insights(portfolio_id, user)
    match = next((item for item in results["data"] if item["id"] == insight_id), None)
    if not match:
        raise HTTPException(status_code=404, detail={"code": "insight_not_found"})
    return {"data": match}


def copilot_evidence(portfolio_id: str, owner_id: str) -> dict:
    summary = analytics_summary(portfolio_id, {"_id": owner_id})["data"]
    exposure_data = exposure(portfolio_id, owner_id)
    insight_data = insights({}, exposure_data)
    return {"summary": summary, "exposure": exposure_data, "insights": insight_data}


@app.post("/api/v1/copilot/chat")
async def copilot_chat(payload: CopilotRequest, user=Depends(current_user)):
    require_portfolio(payload.portfolio_id, user["_id"])
    evidence = copilot_evidence(payload.portfolio_id, user["_id"])
    if not settings.gemini_api_key:
        return {"answer": deterministic_answer(payload.question, evidence), "provider": "deterministic", "evidence": evidence}
    prompt = (
        "Answer only from the JSON evidence. Never invent numeric values. Mention dates and limitations. "
        "Give educational portfolio analysis, not buy/sell instructions. If the evidence does not answer the question, say so.\n"
        f"Evidence: {evidence}\nQuestion: {payload.question}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, params={"key": settings.gemini_api_key}, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 450}})
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"answer": text, "provider": "gemini", "evidence": evidence}
    except Exception as exc:
        logger.info("Gemini unavailable; deterministic fallback (%s)", type(exc).__name__)
        return {"answer": deterministic_answer(payload.question, evidence), "provider": "deterministic_fallback", "evidence": evidence}


def deterministic_answer(question: str, evidence: dict) -> str:
    top = evidence["exposure"]["companies"][:3]
    if not top:
        return "I do not have mapped company holdings to answer that yet. Import holdings and add verified fund disclosures first."
    items = "; ".join(f"{row['name']} represents {row['portfolio_percentage']:.1f}% of portfolio value" for row in top)
    return f"Based on the currently mapped exposure, {items}. Look-through coverage is {evidence['exposure']['coverage_percentage']:.1f}%. These figures use the latest loaded fund disclosures; incomplete or stale mappings can understate exposure."


@app.get("/api/v1/copilot/conversations")
def conversations(user=Depends(current_user)):
    return {"data": [jsonable(row) for row in get_db().conversations.find({"user_id": user["_id"]}).sort("created_at", -1).limit(50)]}

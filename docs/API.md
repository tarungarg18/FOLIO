# API Reference

Base URL: `http://localhost:8000/api/v1`. Interactive OpenAPI documentation is available at `/docs`.

## Health

- `GET /health` returns API and MongoDB availability.

## Authentication

- `POST /auth/register` body `{ "email", "password", "name" }`.
- `POST /auth/login` body `{ "email", "password" }`; sets HttpOnly `folio_session` cookie.
- `POST /auth/logout` revokes current session.
- `GET /auth/me` returns current account.
- `POST /demo/open` creates/opens the labelled illustrative demo account and session.

## Portfolio and holdings

- `GET /portfolios`
- `GET /portfolios/{portfolio_id}`
- `GET /portfolios/{portfolio_id}/holdings`
- `POST /portfolios/{portfolio_id}/holdings`
- `PUT /holdings/{holding_id}`
- `DELETE /holdings/{holding_id}`

Holding body: `{ "instrument_id": "...", "asset_type": "equity|mutual_fund|cash|debt", "quantity": 1, "average_cost": 0, "scheme_code": "..." }` (scheme code required for mutual funds).

## CSV import

- `POST /portfolios/{portfolio_id}/import/preview` multipart field `file`; CSV requires `asset_type`, `quantity`, and one of `symbol`, `isin`, `scheme_code`.
- `POST /portfolios/{portfolio_id}/import/confirm` body `{ "rows": [HoldingInput, ...] }`; every instrument must already exist in the instrument master.

Preview never saves rows. Unknown mappings require review. Upload limit is 2 MB.

## Market and analytics

- `GET /market/instruments?q=...`
- `GET /market/data-health`
- `GET /analytics/summary?portfolio_id=...`
- `GET /analytics/allocation?portfolio_id=...`
- `GET /analytics/exposure?portfolio_id=...`
- `GET /analytics/overlap?portfolio_id=...`
- `GET /analytics/risk?portfolio_id=...`
- `GET /analytics/benchmark?portfolio_id=...&benchmark_id=nifty_50_tri`
- `GET /insights?portfolio_id=...`
- `GET /insights/{insight_id}?portfolio_id=...`
- `POST /copilot/chat` body `{ "portfolio_id": "...", "question": "..." }`
- `GET /copilot/conversations`

Risk and benchmark endpoints return explicit unavailable/insufficient-data responses until verified historical series are loaded. Some planned CRUD and conversation persistence are not implemented yet; see the implementation backlog.

# FOLIO Implementation Backlog

Priorities: P0 required for the judge-ready core; P1 supporting hardening if schedule allows; P2 stretch only after P0 passes.

| ID | Priority | Week | Task | Dependencies | Acceptance |
|---|---|---:|---|---|---|
| F01 | P0 | 1 | Audit actual project directory and inspect required Figma frames | None | Record repo state and screen-to-data mapping; preserve existing working code if discovered |
| F02 | P0 | 1 | Test source accessibility, terms, identifiers and sample overlapping fund disclosures | F01 | Source feasibility record supports a real shared-ISIN demo or documents fallback |
| F03 | P0 | 1 | Start Next.js/FastAPI against local MongoDB; add indexes, auth and demo seed | F01 | Local app runs; login/demo route works; ownership enforced |
| D01 | P0 | 2 | Collect selected equity history and corporate actions | F02 | Repeatable script stores correct price basis, coverage, provenance; no duplicate instrument/date |
| D02 | P0 | 2 | Collect NAV history by <=90-day windows and exact scheme metadata | F02 | Scheme code/plan/option verified; dates and NAVs validate |
| D03 | P0 | 2 | Parse selected monthly AMC/AMFI constituent disclosures | F02 | Reporting/publication dates, weights and ISINs stored; actual sample manually reconciled |
| D04 | P0 | 2 | Ingest NIFTY 50 TRI and NIFTY 500 TRI | F02 | Series have verified return type, dates, source, and usage status |
| D05 | P0 | 2 | Instrument mapping, quality checks, manifests and resumability | D01-D04 | Uncertain securities remain unmapped; re-run is idempotent and report lists gaps |
| P01 | P0 | 3 | CSV upload, normalization, preview, validation and confirm | F03 | Invalid/ambiguous rows block or require review; no silent substitution |
| P02 | P0 | 3 | Holding CRUD and current valuation | F03, D01-D02 | Equity uses unadjusted close, funds latest valid NAV, with as-of timestamps |
| A01 | P0 | 3 | Look-through, overlap aggregation, residual assets and precise coverage | D03, P02 | Golden example passes; fund constituents do not inflate total value |
| A02 | P0 | 4 | Fixed-holdings historical return reconstruction | D01-D04, P02 | Series labelled hypothetical; adjustment and common-date rules documented |
| A03 | P0 | 4 | Volatility, drawdown, beta, correlation, HHI, effective holdings | A02 | Hand-calculated tests pass with sample counts and unavailable states |
| A04 | P0 | 4 | Benchmark comparison, health score and deterministic insights | A01-A03 | TRI aligned; score versioned; low coverage never implies low risk |
| U01 | P0 | 4-5 | Build dashboard, holdings and diversification screens | P02, A01 | Values and exposure derive from APIs; Figma hierarchy retained |
| U02 | P0 | 5 | Build risk, benchmark, insights, security detail and Ask Folio | A02-A04 | Required screens render loading, empty, stale and failure states |
| C01 | P0 | 5 | Gemini tool calls, context selection, numerical checks and fallback | A01-A04 | Answers cite actual metrics/dates; quota/provider errors yield deterministic response |
| Q01 | P0 | 6 | API, security, data, browser and clean-start acceptance tests | All P0 | Fresh local setup completes whole demo; cross-user access denied |
| X01 | P2 | 6 | Expand instruments/funds/history | All P0 | Only if core P0 acceptance already passes |

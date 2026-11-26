# FOLIO: Final Six-Week POC Execution Plan

## Executive summary

FOLIO is a local, judge-ready portfolio intelligence proof of concept for Indian retail investors. Its central demonstration is hidden equity exposure: a company owned directly and through multiple mutual funds is aggregated using the fund values and actual dated disclosure weights.

The original competition brief asks for portfolio analysis, health/diversification/risk, hidden exposure, NIFTY benchmark comparison, explainable insights, a conversational interface, dashboard, and API. The working directory contained only `AI_ML_Projects.pdf`; no application source or baseline planning document was found. This plan is the implementation blueprint. Inspect the actual project directory before coding if another repository is intended.

Build one complete journey: open demo portfolio, import CSV and review mappings, value holdings, inspect look-through exposure, review risk and benchmark comparison, inspect evidence-backed insight, ask a grounded copilot question. Trading, prediction, broker integration, streaming prices, broad universe coverage, reports, advanced ML, notifications, multiple portfolios, and native mobile are out of scope.

## Technical architecture

- Frontend: Next.js, TypeScript, Tailwind CSS, Recharts.
- Backend: one FastAPI service using Pydantic, PyMongo, Pandas, NumPy, SciPy.
- Database: local MongoDB Community Server. MongoDB Atlas is not required.
- AI: Gemini called only by the backend through allow-listed analytics tools. Keep its API key in an untracked `.env`; document only the variable name in `.env.example`. Apply a modest request budget, reuse/cached evidence where practical, validate numerical claims, and fall back to deterministic explanations on quota, timeout, malformed response, or provider failure.
- Operations: ordinary Python collection scripts and local native startup. Docker Compose is optional convenience only. No Redis, SQL database, ORM/migration framework, task queue, vector store, LangChain, or agent framework.

Keep modules grouped by API, data sources/ingestion, analytics, and AI orchestration. MongoDB collections: users, sessions, portfolios, holdings, instruments, prices, corporate_actions, fund_schemes, fund_navs, fund_snapshots, fund_constituents, benchmarks, benchmark_values, ingestion_jobs, data_manifests, insights, conversations. Use Decimal128 or integer minor currency units for financial persistence; convert to documented API decimal strings. Add uniqueness indexes for provider/instrument/date, scheme/NAV date, scheme/disclosure/security, benchmark/date; indexes for ISIN, scheme code, owner, and observation date. Maintain a small versioned Python setup script for indexes/schema version.

### API groups (`/api/v1`)

Auth (register/login/logout/me); demo portfolio and holding CRUD; CSV upload/preview/confirm; instrument search and data health; analytics summary/allocation/exposure/overlap/risk/benchmark; insights list/detail; copilot chat/history. Every portfolio operation enforces user ownership. Metric results include as-of date, period, coverage, methodology version, and source/disclosure dates. Errors use stable codes and request IDs.

### Screens and data dependencies

| Screen | Purpose and backend data |
|---|---|
| Login/demo | Authentication and seeded illustrative portfolio |
| Onboarding/import review | CSV parsing, instrument resolution, validation, confirmation |
| Dashboard | Value, return context, health, leading insight, freshness |
| Holdings | Positions and latest valid price/NAV |
| Security detail | Direct value, each fund contribution, combined exposure and source dates |
| Diversification | Company/sector allocation, overlap, coverage and residual assets |
| Risk | Volatility, drawdown, beta, correlation with explanations |
| Benchmark | Aligned portfolio and NIFTY TRI series |
| Insights | Severity, supporting calculations, dates and deep links |
| Ask Folio | Tool-grounded answers, evidence and limitations |

Inspect the referenced Figma frames in Week 1 and implement their composition and visual system. Ensure usable layouts at 1440, 1024, 768, and 390 px. Mobile prioritizes portfolio value, hidden exposure, key insight, and navigation; no horizontal page overflow.

## Data strategy and feasibility gate

No source integration or usage rights were verified in the workspace. Week 1 must test downloads, identifiers, historical depth, terms, and file formats before declaring any source usable. Candidate routes:

| Dataset | Candidate source | Verification and fallback |
|---|---|---|
| Equity OHLCV/actions | Permitted Yahoo/yfinance research access; authorized NSE data | Test a small symbol sample, action fields, five-year gaps, and permitted use. NSE historical products may require subscription. Do not bypass blocks. If no permitted automatic feed, use a documented permitted historical export or reduce the demo scope. |
| Scheme identity and NAV | AMFI | Verify exact scheme code, direct-growth plan, date parsing and history. Fetch history in windows no longer than 90 days. MFapi can be evaluated as a backup and checked against AMFI. |
| Fund constituents | AMFI and AMC monthly disclosures | Test actual spreadsheets/files for dates, ISINs, weights and parsing effort. Prefer machine-readable disclosures. Replace schemes whose data cannot be parsed reliably. |
| NIFTY 50/500 TRI | Nifty Indices historical data | Verify both TRI series, export path, historical coverage and usage conditions. If unavailable, show an empty state; never fabricate a benchmark. |
| Instrument/sector map | ISINs from market/disclosure sources plus reviewed mapping table | ISIN is primary. Fund code plus plan/option identifies scheme. Names alone do not authorize a match. |

Smallest dataset that proves the idea: 8–10 equities, 2–3 schemes with verified disclosures and one company ISIN appearing in at least two selected funds, plus NIFTY 50 TRI and NIFTY 500 TRI. Expand only after that pipeline works. Target five years of daily history where genuinely available; record actual shorter coverage. Select exact tickers and schemes from tested source files, not popularity. HDFC Bank is only an example, conditional on verified overlap. Synthetic quantities and costs are clearly labelled; all prices, NAVs, and fund weights shown as real must be traceable to source records.

Collectors are resumable Python scripts with bounded retries, rate limits, raw-file archive where permitted, normalization, validation, idempotent upserts and manifests. Record provider, URL, retrieval time, market period, disclosure reporting/publication dates, adjustment basis, currency, row count, validation, license/usage status, and checksum. Validate nulls, duplicates, invalid OHLC, missing dates, abnormal returns, corporate actions, NAV discontinuities, invalid weights, and unmapped ISINs. Do not replace valid data with nulls or call a monthly disclosure live.

## Financial methodology

### Valuation, exposure and coverage

- Current direct equity market value = shares × latest valid **unadjusted closing price**. Fund market value = units × latest valid NAV.
- Historical performance uses consistently adjusted historical prices or a correctly reconstructed total-return series accounting for splits and dividends. Keep price and quantity bases consistent; never adjust twice.
- Indirect company value = sum over funds of (fund market value × disclosed company weight). Combined company value = direct value + indirect value. Combined portfolio percentage divides by total portfolio value. Fund constituents decompose fund assets; never add them again to portfolio value.
- Coverage = `verified mapped eligible exposure / total eligible exposure × 100`. Eligible exposure is direct equity plus the equity portion of mutual funds included in look-through. Report debt, cash, other ineligible assets, and unmapped eligible exposure separately. Missing coverage reduces confidence and must never be treated as low risk.

Golden example: total portfolio ₹10,00,000; direct company value ₹80,000; Fund A ₹2,00,000 at 8%; Fund B ₹1,00,000 at 5%. Indirect = ₹16,000 + ₹5,000 = ₹21,000. Combined = ₹1,01,000 or 10.1%. Portfolio total remains ₹10,00,000.

### Historical returns and risk

A holdings CSV with average cost lacks complete cash flows. Construct a labelled hypothetical fixed-current-holdings buy-and-hold series from historical security prices/NAVs. Do not call it actual investor performance, realized P&L, TWR, or XIRR. Use common valid dates; document staleness limits and do not silently fill missing trading observations. Current value uses unadjusted close; historical returns use adjusted/total-return series consistently.

- Volatility: sample standard deviation of daily returns × √252.
- Maximum drawdown: minimum of value divided by running peak minus one.
- Beta: covariance of aligned portfolio and benchmark daily returns divided by benchmark return variance.
- Correlation: Pearson correlation on shared return dates; disclose sample count.
- HHI: sum squared company exposure fractions; effective holdings = 1/HHI when mapped coverage supports interpretation.
- Benchmark comparison rebases portfolio and TRI to the first common date and uses the same end date. Label the portfolio reconstruction hypothetical. Insufficient overlap yields unavailable state.
- Sharpe requires a dated, documented risk-free series. XIRR requires complete dated cash flows. Omit otherwise.

Health Score v1 weights: diversification 30%, security/sector concentration 25%, volatility 20%, drawdown 15%, coverage/freshness 10%. Before implementing, document component thresholds, normalization/clamping, minimum sample counts, missing-component handling, and methodology version. Missing inputs yield incomplete/low-confidence score; never a favorable default.

### Insights and Gemini

Deterministic insights cover company/sector concentration, repeated fund constituents, overlap, high correlation, drawdown deterioration, benchmark underperformance, and incomplete/stale coverage. Each insight contains rule, calculation inputs, severity, date, coverage and destination.

Gemini can use only backend functions: `get_summary`, `get_allocation`, `get_exposure`, `get_overlap`, `get_risk`, `get_benchmark`, `get_insights`, and `get_data_health`. The backend scopes evidence to the authenticated portfolio, supplies only relevant computed values, verifies numerical claims against tool output, and returns source/disclosure dates. Unsupported questions state what data is missing. Gemini failure never blocks analytics or dashboard use.

## Six-week schedule and backlog

| Week | Work | Exit criterion |
|---|---|---|
| **1 Foundation** | Confirm directory/repository, inspect Figma, test source access/terms and freeze minimum dataset. Set up MongoDB, API contracts, indexes, methodology, auth, local startup and shell. | App starts locally and login works; source record proves candidate overlapping disclosures and both TRI acquisition paths or records an explicit fallback. |
| **2 Real data** | Implement price/action, NAV, disclosure and TRI collectors; mapping, validation, provenance, freshness, checkpoint/resume. Prioritize minimum dataset. | Repeatable bootstrap yields real traceable records, no duplicate keys, and quality report. |
| **3 Core innovation** | CSV preview/confirm, holding CRUD, current valuation, ISIN mapping, look-through, overlap and coverage. | Direct plus two-fund exposure matches golden example and is visible with source dates. |
| **4 Intelligence** | Hypothetical historical series, risk, benchmarks, HHI, health score, deterministic insights; begin connected UI. | Independent fixtures pass and missing inputs remain explicit. |
| **5 Product** | Complete required Figma screens, responsive/error/empty states, grounded Gemini and fallback. | Full demo journey works at desktop and mobile; no visible dead controls. |
| **6 Finalization** | Integration/security/browser tests, clean setup, fixes, docs, demo rehearsal. Freeze features midweek. | Fresh setup reproduces ingestion and full demo; all P0 tests pass. |

P0 backlog: verify repo/Figma/data; local app and MongoDB; source collectors; mapping/quality report; import review; look-through and coverage; risk/benchmark; health/insights; required screens; Gemini grounding/fallback; automated acceptance suite. P2: more instruments, funds or disclosure history only after P0 completion.

## Test and judge acceptance

Automated tests cover local MongoDB connectivity/index creation, repeated ingestion, duplicate/invalid records, scheme and ISIN mapping, CSV preview/confirmation/rejection, unadjusted current valuation, corporate-action-consistent historical returns, multi-fund aggregation without double-counting, exact coverage denominator and residual classification, risk formulas, common-date TRI comparison, ownership isolation, Gemini number grounding/quota fallback, required frontend routes and 1440/1024/768/390 px layouts. Use hand-calculated independent fixtures.

Judge flow: open labelled demo portfolio; upload and review CSV; show current value; inspect company held directly and through at least two funds; verify combined exposure, disclosure dates and mapping coverage; open risk insight; compare hypothetical historical series to NIFTY 50 TRI; ask Gemini why concentration is elevated and inspect supporting calculation/source.

Biggest risks are permitted source access, inconsistent AMC file formats, incomplete ISIN mapping and frontend integration time. Gate expansion on a real, permitted shared-ISIN fund disclosure set. Change funds/security selection or reduce universe if that gate fails.

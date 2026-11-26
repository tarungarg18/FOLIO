# FOLIO POC Acceptance Criteria

## Data and database

- A clean local setup connects to MongoDB Community Server, creates required indexes, and loads the demo seed.
- Re-running each collector produces no duplicate instrument/date, scheme/date, disclosure/security, or benchmark/date records.
- A quality report identifies missing dates, invalid prices/NAVs, bad weights, unmapped identifiers, stale disclosures, source status, and coverage.
- Every displayed market observation can be traced to provider, source, retrieval date, and relevant market/disclosure date.

## Portfolio and calculations

- CSV preview reports accepted, invalid, duplicate, and ambiguous rows before confirmation; unknown instruments are never silently remapped.
- Current equity value uses shares × latest valid unadjusted closing price; fund value uses units × NAV.
- Historical price returns use a consistent adjustment or total-return basis with corporate actions accounted for once.
- A portfolio containing direct company holdings and two funds aggregates direct plus both indirect contributions without adding fund constituents to total portfolio value.
- Golden example: ₹10,00,000 portfolio; ₹80,000 direct; Fund A ₹2,00,000 × 8%; Fund B ₹1,00,000 × 5%. Indirect ₹21,000; combined ₹1,01,000 or 10.1%; total remains ₹10,00,000.
- Coverage equals verified mapped eligible exposure divided by total eligible exposure × 100. Debt, cash, other ineligible, and unmapped eligible exposure are separately reported; missing coverage is not low risk.
- Hypothetical current-holdings history is labelled as such; no unsupported realized P&L, TWR, XIRR, or actual investor performance is claimed.
- Volatility, drawdown, beta, correlation, HHI, effective holdings, benchmark rebasing, and health score match independent known fixtures or explicitly show unavailable inputs.

## API and AI

- API tests verify CSV lifecycle, holding CRUD, structured validation errors, and ownership isolation between users.
- Analytics include as-of date, period, coverage, methodology version, and data source dates.
- Gemini can answer from allow-listed analytics tools only; its numeric claims match tool outputs, and evidence dates are included.
- Gemini quota, network failure, malformed response, or unsupported question produces a clear deterministic fallback/limitation.

## Frontend and delivery

- Every required Figma screen is connected to real data/API behavior; no visible dead controls.
- Empty, loading, stale-data, partial-coverage, validation, and provider-error states are handled.
- Dashboard makes value, principal exposure/risk observation, and data freshness clear immediately.
- Diversification shows the direct and indirect components and dates behind combined exposure.
- Routes and critical flows work at 1440, 1024, 768, and 390 px without horizontal page overflow.
- A fresh local setup can bootstrap the minimum data and complete the judge demonstration: demo, CSV import, valuation, shared-company look-through, risk, TRI comparison, insight, and grounded copilot answer.

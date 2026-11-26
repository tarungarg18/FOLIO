# Data Sources and Usage

## Status

No source has been verified or integrated in this repository. This POC does not claim live data. Before ingestion, verify retrieval access, identifier quality, date coverage, and applicable terms. Do not bypass access controls or redistribute data without permission.

Candidate sources:

- Equity history/actions: authorized NSE data or research access through Yahoo/yfinance where its terms permit the intended use.
- Mutual fund NAV: AMFI historical NAV, requested in windows no longer than 90 days; optional MFapi comparison.
- Fund holdings: actual dated AMFI/AMC scheme disclosures; prefer machine-readable files and preserve reporting/publication dates.
- Benchmarks: Nifty Indices historical NIFTY 50 TRI and NIFTY 500 TRI series.

Each loaded dataset must have a manifest with provider, source URL, retrieval timestamp, covered dates, reporting/publication dates where relevant, currency, adjustment basis, record count, validation status, usage status, and checksum where possible. Data-health API returns manifests. Monthly fund holdings are historical snapshots, not live positions.

For detailed source qualification and fallback strategy, see `planning/DATA_SOURCE_FEASIBILITY.md`.

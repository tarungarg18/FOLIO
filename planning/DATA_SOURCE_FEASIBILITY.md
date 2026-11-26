# FOLIO Data Source Feasibility

## Status

No provider was tested from the application environment yet. The following are candidates, not verified integrations or granted redistribution rights. Week 1 must run small sample downloads and review applicable terms before implementation depends on a source.

| Dataset | Candidate | Method/depth | Identifiers | Restrictions and failure plan |
|---|---|---|---|---|
| NSE equity EOD and actions | Authorized NSE product or permitted Yahoo/yfinance research access | Sample 8-10 symbols, target five years daily where available; validate actions and gaps | ISIN/NSE symbol from instrument reference; Yahoo ticker is secondary | NSE historical products may require subscription. yfinance is unofficial; Yahoo terms govern underlying data. If blocked or not permitted, use documented permitted export or reduce universe; never bypass controls. |
| Mutual fund NAV | AMFI historical NAV | Batch date ranges <=90 days; daily scheme NAV | Scheme code, exact name, plan and option | Verify parsing and access. MFapi is optional backup and sample values must be checked against AMFI. |
| Fund monthly constituents | AMFI scheme disclosure and individual AMC disclosure pages | Obtain actual spreadsheet/PDF, latest snapshot and older snapshots if practical | Security ISIN where disclosed; fund scheme code | Layouts differ; automate only formats validated on real files. Replace a hard-to-parse scheme. Report stale or unmapped holdings. |
| TRI benchmarks | Nifty Indices historical data | Export NIFTY 50 TRI and NIFTY 500 TRI, verify date span | Index name and return type | Check access/usage rights and export behavior. If absent, show benchmark unavailable; do not substitute price index silently. |
| Sector/instrument reference | Official available identifier files and reviewed mapping | Import and curate small selected universe | ISIN primary | No fuzzy-name merge without review; unknown rows remain unmapped. |

## Minimum demo dataset

Start with 8-10 equities, two or three funds whose latest verified disclosures share one constituent ISIN, and both named TRI series. Grow to 15-20 equities and 6-8 schemes only after the smaller set works. Exact symbols and scheme codes are chosen from files successfully downloaded and inspected during Week 1. HDFC Bank is a possible example only if it appears in the selected actual disclosures. Synthetic quantities and costs are allowed and clearly labelled; prices, NAVs, and fund weights are sourced data.

## Collection and quality rules

Collectors are plain Python scripts with explicit date windows, checkpoints, bounded retries, idempotent writes, source timestamps and clear progress/errors. Preserve raw data only where permitted. Manifests include provider, source URL, retrieval timestamp, covered dates, reporting date, publication date, adjustment basis, currency, count, validation outcome, usage status and checksum.

Reject or flag duplicates, null/zero/negative prices, invalid OHLC ordering, suspicious movements, missing sessions, action inconsistencies, NAV gaps, invalid fund weights, duplicate constituents, unknown ISINs and stale disclosures. Never claim full coverage if records are unmapped. A provider failure must not erase previously valid values.

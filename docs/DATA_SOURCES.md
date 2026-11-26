# Demo Data Sources

`backend/scripts/bootstrap_demo_data.py` downloads a deliberately small, dated demo dataset. The raw files are kept under `data/raw/demo/`, which is git-ignored. Do not commit downloaded market or disclosure files.

| Data | Source used | Basis and limitation |
|---|---|---|
| NSE equity prices | Yahoo Finance chart endpoint (`query2.finance.yahoo.com`) | Unofficial research-oriented endpoint. Uses unadjusted close for current valuation and adjusted close for historical reconstruction. Check Yahoo's current terms before redistribution. |
| Mutual fund NAV history | MFAPI (`api.mfapi.in`), cross-checked against the official AMFI latest NAV file | MFAPI is a third-party mirror; AMFI latest NAV and scheme identity must match before data is accepted. Check MFAPI terms before redistribution. |
| PPFAS Flexi Cap holdings | PPFAS AMC monthly portfolio workbook, reporting date 30 Sep 2026 | Actual disclosed holdings and ISINs. A monthly disclosure is a dated snapshot, not live fund holdings. |
| SBI Flexicap holdings | SBI Mutual Fund all-schemes monthly workbook, reporting date 31 Oct 2026 | Actual disclosed holdings and ISINs. A monthly disclosure is a dated snapshot, not live fund holdings. |
| NIFTY 50 / 500 benchmark | Yahoo Finance symbols `^NSEI` and `^CRSLDX` | Price-index series only; dividends are excluded. The official Nifty Indices TRI endpoint redirected to a login page during verification, so the demo does not label these series as TRI. |

The remote requests were tested from the development environment. This confirms technical accessibility at that time; it is not a license grant. The seed script stores source URLs, retrieval time, period, validation status and checksums where available. Terms and redistribution rights remain an operator responsibility.

## Sample portfolio

`data/demo/sample_portfolio.csv` contains illustrative investor quantities and no asserted purchase costs. Its symbols and scheme codes are mapped to real instruments. It does not contain market prices or NAVs. Valuation and histories are downloaded from the providers above when bootstrapping the local demo.

## Fallback behavior

- A provider timeout, malformed response, too-short history, or scheme mismatch stops the bootstrap with a clear error; it does not insert placeholder prices.
- Yahoo is unofficial and may throttle or change its response. Retry later or use a separately reviewed, permitted data export with the normalized CSV ingestion script.
- The official Nifty TRI endpoint was not accessible without login during verification. The Yahoo price-index fallback is clearly labeled and excludes dividends. Replace it only with a licensed/authorized TRI export; never relabel price returns as TRI.
- Fund disclosures are pinned to dated official AMC workbooks. Update the URLs and reporting dates only after verifying the actual published files.

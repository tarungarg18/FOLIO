# FOLIO

Portfolio intelligence for Indian retail investors. FOLIO focuses on what an investor owns directly and through mutual funds, using dated and traceable market data.

## Current project status

The local POC includes a sourced demo data bootstrap, illustrative sample holdings CSV, portfolio valuation and fund look-through, historical reconstruction, risk and benchmark views, CSV review/import, and a responsive dashboard. Provider access and data rights can change; source dates and usage limitations are recorded in `docs/DATA_SOURCES.md`.

## Requirements

- Python 3.11+
- Node.js 20+
- Local MongoDB Community Server running on `mongodb://localhost:27017`
- Optional Gemini key for copilot model responses; deterministic answer works without it

## Run locally

From repository root, copy `.env.example` to `.env` and set values for your machine. Never commit `.env`.

Backend (PowerShell):

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app
```

Frontend, in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`; API docs are at `http://localhost:8000/docs`. Health endpoint: `http://localhost:8000/health`.

## Load the demo portfolio

After starting local MongoDB and installing backend requirements, run once from `backend`:

```powershell
python -m scripts.bootstrap_demo_data
```

This downloads dated source data into the ignored `data/raw/demo/` directory and seeds the local MongoDB database. Sample quantities are illustrative; current values use downloaded closes/NAVs. Historical fund holdings are monthly disclosures, not live holdings. Yahoo's price-index benchmark excludes dividends and is not TRI. Check provider terms before redistributing downloaded data.

The matching sample CSV is available from the dashboard's **Example CSV** link or at `data/demo/sample_portfolio.csv`. CSV import previews instrument matches and requires confirmation before positions are saved.

## Core financial conventions

- Current equity valuation uses quantity times latest valid unadjusted close.
- Historical returns require a consistent adjusted/total-return basis and corporate actions applied once.
- Fund holdings explain fund exposure and are not added again to total portfolio value.
- Coverage is verified mapped eligible exposure divided by total eligible exposure. Debt, cash, other assets, and unmapped eligible amounts are identified separately.
- Incomplete coverage is not evidence of lower risk.

## Project references

Product documentation is under `docs/`. Planning, backlog, feasibility notes, architecture learning material, and acceptance plan are grouped under `planning/` so they remain separate from product documentation. No plan document is presented as completed functionality.

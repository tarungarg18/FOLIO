# FOLIO

Portfolio intelligence for Indian retail investors. FOLIO focuses on what an investor owns directly and through mutual funds, using dated and traceable market data.

## Current project status

This repository is the initial POC foundation. The API, local MongoDB integration, CSV preview, basic portfolio valuation/look-through, Gemini fallback, and responsive dashboard shell are present. Provider-specific data adapters, verified source data, full authentication UI, historical risk/benchmark series, and complete Figma screen set are not complete. The app intentionally shows unavailable states rather than fabricated market figures.

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

## Data loading

Remote provider retrieval is deliberately not enabled until access and usage conditions are verified. Download and inspect permitted provider files, then use the CSV ingestion utility described in `docs/DATA_DICTIONARY.md`. Run validation with:

```powershell
cd backend
python -m scripts.validate_dataset
```

The sample investor positions, if added, must be labelled illustrative. Do not treat a fund's monthly holdings as live holdings.

## Core financial conventions

- Current equity valuation uses quantity times latest valid unadjusted close.
- Historical returns require a consistent adjusted/total-return basis and corporate actions applied once.
- Fund holdings explain fund exposure and are not added again to total portfolio value.
- Coverage is verified mapped eligible exposure divided by total eligible exposure. Debt, cash, other assets, and unmapped eligible amounts are identified separately.
- Incomplete coverage is not evidence of lower risk.

## Project references

Product documentation is under `docs/`. Planning, backlog, feasibility notes, architecture learning material, and acceptance plan are grouped under `planning/` so they remain separate from product documentation. No plan document is presented as completed functionality.

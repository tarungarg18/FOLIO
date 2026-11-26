# Local Development

## Services

1. Install and start MongoDB Community Server locally at `mongodb://localhost:27017`.
2. Copy root `.env.example` to `.env`; set local values and optionally a rotated Gemini API key. Never commit `.env`.
3. Create a Python 3.11 virtual environment in `backend`, activate it, install `requirements.txt`, and run `python -m app`.
4. In `frontend`, run `npm install` and `npm run dev`.
5. Visit `http://localhost:3000`. API docs: `http://localhost:8000/docs`.

Local data scripts require an active MongoDB instance. Remote data connectors must be configured only after verifying source availability and usage terms. The demo positions are illustrative and do not fabricate prices; until source files are loaded, the UI displays unavailable states.

Docker packaging is optional and not required for setup.

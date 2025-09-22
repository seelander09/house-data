# Realtor Lead Radar

An end-to-end platform for scouting high-potential real estate listings using the Realie Property Data API. The project pairs a FastAPI backend that scores and filters properties with a React/Chakra UI dashboard for realtor-facing workflows.

## Project Layout
- `backend/` – FastAPI application with Realie integration, scoring engine, and REST endpoints.
- `frontend/` – React + Vite dashboard featuring filters, lead exports, and scoring visuals.
- `docs/` – Architecture notes and design references.
- `scripts/` – Orchestration helpers for starting/stopping the full stack.

## Prerequisites
- Python 3.11+
- Node.js 18+
- Install backend deps (`pip install -r backend/requirements.txt`) and frontend deps (`npm install` in `frontend/`).
- Set `REALIE_API_KEY` inside `backend/.env`.

## One-Command Orchestration
The `scripts/start_stack.py` and `scripts/stop_stack.py` helpers launch and tear down both services with logging and retries.

```bash
# Start backend (uvicorn) and frontend (Vite) together
python scripts/start_stack.py

# Stop everything that was launched by the start script
python scripts/stop_stack.py
```

Features:
- Writes service logs to `logs/backend.log` and `logs/frontend.log`, plus orchestration events to `logs/stack_manager.log`.
- Retries failed starts (3 attempts per service) and waits for the expected ports (backend 8100, frontend 5174).
- Performs a `/health` HTTP check for the backend so missing environment variables will halt startup early.
- Persists process IDs in `logs/stack_state.json` so the stop script knows what to terminate.
- Gracefully stops services (SIGTERM) with a force-kill fallback when needed.

> The scripts assume you already created the backend virtualenv (`backend/.venv`) and installed dependencies for both services. If startup fails, check the log files in `logs/` for details.

## Manual Backend Setup (optional)
```bash
cd backend
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env  # add REALIE_API_KEY
uvicorn app.main:app --reload
```

### API Endpoints
- `GET /api/properties` – Fetch scored properties with filters (`city`, `state`, `min_equity`, `min_score`, `search`, `limit`, `offset`).
- `GET /api/properties/export` – Download filtered results as CSV.
- `POST /api/properties/refresh-cache` – Force-refresh the upstream cache.

## Manual Frontend Setup (optional)
```bash
cd frontend
npm install
cp .env.example .env  # optionally override VITE_API_BASE_URL
npm run dev
```

The dev server proxies API requests to `http://localhost:8100/api` by default.

## Testing
- Backend: `cd backend && .\.venv\Scripts\python -m pytest`
- Frontend: `cd frontend && npm run test -- --run`

## Key Features
- Real-time property scoring tuned via configurable weights and background refresh.
- Advanced filtering: absentee vs owner occupants, value gap thresholds, market/assessed ranges, and radius search.
- Lead packs API + dashboard drawer for bundling the highest-scoring opportunities per market.
- Outreach playbook drawer with email/SMS templates and quick call/email actions from the grid.
- Debounced, preset-aware filters with persistent saved searches for repeat campaigns.
- Usage metering captures exports, lead packs, and cache refreshes with `/api/usage/summary` plus plan-aware `/api/usage/plan` snapshots for billing analytics.

## Usage Metering & Plans
- Attach optional `X-Account-Id`/`X-User-Id` headers to requests to scope metering data per organisation or seat.
- Plan quotas are enforced on lead-pack generation, exports, and cache refreshes. Limits return `429` responses with descriptive messaging.
- Retrieve plan health (including alerts when you are within 10% of a limit) via `GET /api/usage/plan`.
- React dashboard surfaces plan usage, disables quota-bound actions, and surfaces alerts as quotas tighten.

See `docs/architecture.md` for additional technical background and future enhancements.

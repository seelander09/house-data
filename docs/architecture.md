# Realtor Lead Radar Architecture

## Stack Overview
- **Backend**: FastAPI (Python 3.11), running under Uvicorn.
- **HTTP Client**: `httpx` for Realie API calls with request-level timeouts and retries.
- **Caching**: In-memory cache with TTL to avoid hammering the Realie API while keeping data fresh.
- **Frontend**: React 18 + Vite + TypeScript, styled with Chakra UI for responsive, professional UI.
- **State Management**: React Query for API data fetching/caching, Zustand for lightweight UI state.
- **Build & Tooling**: pnpm for frontend dependencies, task scripts in root `Makefile` (or PowerShell equivalents) to run backend and frontend together.
- **Testing**: Pytest for backend service layer, Vitest + React Testing Library for UI.

## Data Flow
1. Frontend requests `/api/properties` with optional filters (`city`, `state`, `min_equity`, `min_score`, `limit`).
2. Backend checks the cache. If cache is stale (>5 minutes) or forced refresh, it pulls fresh data from Realie API.
3. Backend normalises data, computes a `listingScore` per property, and returns results paginated + sorted.
4. Frontend renders a sortable, filterable grid. Users can export current filters via `GET /api/properties/export` (CSV).

## Scoring Model
Score = weighted sum of:
- **Equity factor (0.45)**: Higher current estimated equity.
- **Value delta (0.35)**: Gap between estimated market value and assessed value when available.
- **Recency factor (0.20)**: Penalises old transfers; boosts recent activity (< 2 years).

Each factor is normalised per dataset pull with guardrails for missing data (uses medians).

## Key Modules (Backend)
- `app/config.py`: Settings + env management.
- `app/clients/realie.py`: HTTP wrapper with retries/error handling.
- `app/services/properties.py`: Caching + scoring engine.
- `app/api/routes/properties.py`: API endpoints and query validation.
- `app/models.py`: Pydantic models for responses.

## Key Modules (Frontend)
- `src/api/client.ts`: Axios instance + React Query hooks.
- `src/components/PropertyGrid.tsx`: Main table with Chakra UI and TanStack Table.
- `src/features/filters`: Filter form + Zustand state store.
- `src/pages/Dashboard.tsx`: Orchestrates filters, grid, export action.

## Environment & Secrets
- `.env` stores `REALIE_API_KEY`. `.env.example` committed with placeholders.
- Backend reads key via `pydantic-settings`.

## Deployment Notes
- Backend served via Uvicorn / Gunicorn. Frontend built and served statically (S3/CloudFront or Vercel). For dev, run `uvicorn` + `pnpm dev` concurrently.
- Future: containerise with Docker Compose.

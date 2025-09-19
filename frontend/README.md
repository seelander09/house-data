# Realtor Lead Radar Frontend

A React + Chakra UI dashboard for ranking and filtering high-potential real estate listings sourced from the Realie Property Data API.

## Getting Started

```bash
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` in `.env` to point at the FastAPI backend (default `http://localhost:8000/api`).

## Available Scripts

- `npm run dev` — start Vite dev server with hot reload.
- `npm run build` — build production assets.
- `npm run preview` — preview the production build.
- `npm run test` — run Vitest unit tests (coming soon).

## Tech Stack

- React 18 + TypeScript
- Chakra UI for styling
- TanStack React Query for API data + caching
- TanStack Table for the property grid
- Zustand for global filter state
- Axios for API calls

## Feature Highlights

- Ranking table with score badge tooltips and owner contact details
- Search & filter by address, city, state, minimum equity, and minimum score
- CSV export that respects active filters
- Summary metrics for matched properties
- Built-in React Query Devtools for debugging

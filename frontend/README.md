# Fiber Based Wearable Electronics Patent Mapping - Frontend

React + TypeScript + Vite is the primary UI for the Fiber Based Wearable
Electronics Patent Mapping decision-support tool. It consumes the FastAPI
backend defined in `backend/`, which exposes API routes under `/api` and
delegates reusable logic to `src/`.

## Prerequisites

- Node.js 20 LTS or newer
- npm 10 or newer
- A running FastAPI backend at `http://127.0.0.1:8000`
  (the official Windows launcher is `start_app.bat` from the repository root)

## Setup

```powershell
cd frontend
npm install
copy .env.example .env
```

`.env` is git-ignored. Adjust `VITE_API_BASE_URL` if the backend is not
running on the default `http://127.0.0.1:8000`.

## Scripts

```powershell
npm run dev      # Start Vite dev server at http://127.0.0.1:5173
npm run build    # Type-check and produce a production build in dist/
npm run preview  # Preview the production build locally
```

For the normal single-origin Windows run, use `start_app.bat` from the
repository root. It installs frontend dependencies when needed, builds this
frontend, and starts FastAPI so the React app and API are served from
`http://127.0.0.1:8000`.

## Project structure

```text
frontend/
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  tsconfig.node.json
  .env.example
  src/
    main.tsx              React entry point
    App.tsx               Top-level providers (QueryClient, Router)
    styles/global.css     Plain CSS for the application UI
    api/                  API client modules per backend resource
    types/                TypeScript shapes that mirror FastAPI responses
    routes/               Route table (React Router)
    layout/               Sidebar, Topbar, AppLayout
    pages/                Feature pages for top-level routes
    components/           Shared and patent-specific UI components
```

## Backend endpoints consumed

- `GET /health`
- `GET /api/patents?limit=...`
- `GET /api/patents/search`
- `GET /api/patents/{analysis_id}`
- `GET /api/patents/{analysis_id}/related`
- `GET /api/filters`
- `GET /api/landscape`
- `GET /api/landscape/focused/{analysis_id}`
- `GET /api/insights`
- `POST /api/advanced-ai/run`
- `GET /api/data-sources/status`
- `POST /api/data-sources/load-prepared`
- `POST /api/data-sources/load-demo`

The data-source sample/recovery endpoint reloads the canonical corpus at
`data/raw/fiber_wearable_patents_sources.csv`; it does not load a separate demo
CSV.

## Wording and scope

The frontend describes itself as a **decision-support tool** that surfaces
**relationship strength**, **overlap signal**, **candidate application areas**,
**technology groups**, **optimized grouping**, and **corpus coverage** computed
from a **curated source-labeled corpus**. It frames results as reading aids for
the current corpus, not legal conclusions, exhaustive office-wide coverage,
live patent-office data fetching, PSO, or autonomous decision-making claims.

## Relationship to the backend

The React frontend consumes the FastAPI backend, which in turn delegates to
reusable services in `src/`. No analysis or storage logic should be duplicated
on the frontend.

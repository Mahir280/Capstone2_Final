# Fiber Based Wearable Electronics Patent Intelligence Workspace

Academic capstone project:
**Determination of Applications in Fiber Based Wearable Electronics Area using a Software Supported by Patent Mapping Algorithm and Biomimetic AI**

This repository contains a React + Vite + TypeScript frontend backed by a
FastAPI API layer for exploring a curated fiber-based wearable electronics
patent corpus. The app supports patent search, patent profile review,
related-patent analysis, patent landscape mapping, dataset insights,
data-source loading, and optional Advanced AI optimization for technology
grouping.

FastAPI exposes JSON routes under `/api`. For production-style local runs, the
same FastAPI process serves the built React frontend from a single origin. Core
reusable logic for import, storage, analysis, insights, and visualization data
structures lives in `src/`.

The application is intended as a research and decision-support tool. It helps
students, reviewers, and researchers read the curated patent landscape more
efficiently, while keeping legal and coverage limits explicit.

## What The App Does

- Searches saved patent records by patent ID, title, organization, country,
  keyword, authority, and application-area language.
- Shows readable Patent Profile pages with source authority, key facts,
  important technical keywords, candidate application areas, and related
  patents.
- Builds related-patent signals from text similarity, shared keywords, and
  technology grouping.
- Displays a Patent Landscape map where patents are shown as connected
  technology neighborhoods.
- Summarizes the dataset by authority, import method, organization, country,
  year, keyword, and missing metadata.
- Provides optional Advanced AI optimization that compares standard technology
  grouping with optimization-selected grouping settings.
- Stores records locally in SQLite so the app can be used without live
  patent-office connections.

## Tech Stack

- React, Vite, and TypeScript for the frontend
- FastAPI for the backend/API layer
- Python reusable services in `src/`
- scikit-learn for TF-IDF text features and KMeans grouping
- NetworkX for patent landscape graph structures
- SQLite through Python's standard `sqlite3`
- pytest, Ruff, and Black for repository checks

## How To Run On Windows

The official Windows launcher is:

```powershell
.\start_app.bat
```

Double-click `start_app.bat` or run it from PowerShell/CMD. It checks Python,
creates `.venv` when needed, installs or updates Python dependencies from
`requirements.txt`, checks Node.js/npm, installs frontend dependencies when
needed, builds the React frontend, and starts FastAPI.

Open http://127.0.0.1:8000 after the server starts. The built React app and
FastAPI JSON routes are served from the same origin. React Router client routes
such as `/patents/USPTO%3AUS-SENSOR-1`, `/landscape`, `/insights`,
`/advanced-ai`, and `/data-sources` work on hard refresh because FastAPI
returns the SPA shell for unmatched non-API paths. API docs remain at
http://127.0.0.1:8000/docs.

### Manual Development Run

For manual backend/frontend development, run the commands directly in separate
terminals.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 for the Vite dev server. The React app calls the
FastAPI backend cross-origin during development; CORS is configured for
`http://localhost:5173` and `http://127.0.0.1:5173`.

## Dataset And Local Storage

The current dataset is a curated, source-labeled academic dataset built from
public patent data sources and structured for analysis in this application.

- `data/raw/fiber_wearable_patents_sources.csv` is the canonical raw corpus and
  default prepared corpus. It currently contains 1166 curated fiber-based
  wearable electronics patent records: 508 USPTO records, 654 EPO records, and
  4 TURKPATENT records.
- On backend startup, FastAPI constructs the shared pipeline service and syncs
  the local SQLite database from the canonical curated CSV when the runtime
  database is empty or stale.
- The sample corpus action in Dataset Coverage is a recovery/testing path that
  reloads the same canonical corpus; it is not a separate static patent dataset.
- Manual CSV/JSON import is available from the Data Sources page for externally
  prepared patent records.
- The final corpus schema and quality expectations are documented in
  `docs/canonical_corpus.md`.

The included records describe the current corpus only. The app does not fetch
from live EPO, USPTO, or TURKPATENT/TPO endpoints in this version.

## Documentation

- `docs/architecture.md` explains the application layers and technical
  boundaries.
- `docs/module_boundaries.md` describes ownership across the frontend,
  backend, and reusable Python modules.
- `docs/pipeline.md` follows the analysis workflow from import to UI response.
- `docs/canonical_corpus.md` documents the canonical dataset schema, quality
  rules, and review queue.
- `docs/collection_workflow.md` and `docs/bigquery_patent_query.sql` describe a
  reproducible public-data collection method.
- `docs/limitations.md` states the interpretation and coverage boundaries.
- `docs/demo_script.md` provides a concise presentation walkthrough.

## Project Structure

```text
backend/
  main.py              FastAPI application factory
  api/                 HTTP routes under /api + Pydantic response schemas
  core/                Backend config + SPA static-serving helper
frontend/
  src/                 React + TypeScript source (Vite)
  dist/                Built React app (generated, git-ignored)
src/
  application/         UI/API-facing service DTO assembly
  acquisition/         CSV/JSON import
  clustering/          Technology grouping and related-patent mapping
  config/              Local settings
  features/            Text feature preparation
  insights/            Dataset, application-area, and overlap-signal services
  models/              Patent records and enums
  optimization/        Advanced AI grouping optimization
  preprocessing/       Record normalization
  services/            Application workflow coordination
  storage/             SQLite persistence
  visualization/       Patent landscape graph structures
data/
  raw/                 Canonical raw corpus and review-needed templates
  processed/           Local runtime database folder
  exports/             Local export folder
docs/                  Supporting project documentation
tests/                 Automated tests
```

## Testing And Quality Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
cd frontend
cmd /c npm run build
```

## Safe Claim Boundaries

- This is a decision-support and reading-aid application.
- Related-patent results are similarity-based signals, not legal conclusions.
- The overlap signal is exploratory and must not be treated as a legal finding.
- Candidate application areas are suggestions from stored patent text, not
  market forecasts.
- Technology groups are produced from the saved dataset and may change with
  different records or settings.
- Advanced AI optimization compares grouping settings; it does not guarantee
  perfect categories, legal outcomes, or market success.

## Repository Hygiene

Do not upload generated runtime files:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.ruff_cache/`
- `.coverage`
- `htmlcov/`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/tsconfig.tsbuildinfo`
- local SQLite databases such as `data/processed/*.sqlite3`
- temporary logs or local export artifacts

Keep the canonical corpus in `data/raw/`. The `.gitignore` is configured to
preserve the canonical corpus and future review-needed collection file while
ignoring runtime output.

## Future Work

Future versions could add official patent-office source-ingestion connectors,
broader validated datasets, richer semantic search, and additional export
workflows. Those items are not implemented in this version.

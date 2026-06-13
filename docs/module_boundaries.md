# Module Boundaries

## `frontend/`

Contains the React + Vite + TypeScript UI. It owns client-side routes,
page composition, API client modules, and TypeScript response shapes. It should
consume FastAPI responses and should not duplicate analysis, storage, import, or
grouping logic.

## `backend/`

Contains the FastAPI backend/API layer. It owns HTTP routing, Pydantic
schemas, dependency wiring, CORS settings, health/docs endpoints, and optional
static serving for `frontend/dist/`. API routes are served under `/api`.
Backend route handlers should remain thin and delegate analysis and persistence
work to reusable `src/` services.

## `src/application/`

Builds UI/API-facing DTOs and orchestration wrappers from reusable domain
services. This layer keeps FastAPI routes from reaching into low-level
internals.

## `src/services/`

Coordinates application workflows and wires settings to storage and analysis
steps. It should stay thin and avoid owning low-level parsing, database, or
visualization code.

## `src/storage/`

Owns local persistence details. The current implementation uses direct
`sqlite3` initialization without an ORM.

## `src/preprocessing/`

Owns text and record preparation boundaries after acquisition/import.
Normalization and cleaning return or operate on canonical models.

## `src/acquisition/`

Owns local CSV and JSON import boundaries. Live EPO, USPTO, and TURKPATENT/TPO
source adapters, API clients, and scraping workflows are not implemented in
this repository.

## `src/models/`

Contains canonical dataclasses and shared enums. Models should remain plain,
explicit, and independent of UI or storage implementation details.

## `src/features/`, `src/clustering/`, `src/insights/`, `src/optimization/`, `src/visualization/`

Own analysis-specific logic for text features, technology groups, relationship
strength, overlap signal, candidate application areas, Genetic Algorithm
grouping optimization, and patent landscape graph data. PSO is not implemented.

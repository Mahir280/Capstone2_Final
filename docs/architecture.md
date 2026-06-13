# Architecture

This project is a single-repository patent intelligence application with a
React + Vite + TypeScript primary frontend, a FastAPI primary backend/API layer,
reusable Python logic in `src/`, and local SQLite runtime storage.

## Core Shape

- `frontend/` owns the React UI, client-side routing, API client code,
  and TypeScript response shapes.
- `backend/` owns the FastAPI app, HTTP routes, Pydantic schemas, dependency
  wiring, CORS settings, and optional static serving for the built React app.
- FastAPI exposes JSON API routes under `/api`; `/health`, `/docs`, and
  `/openapi.json` remain backend routes outside that API prefix.
- When `frontend/dist/` exists, FastAPI can serve the built React frontend from
  the same origin as the API and return the SPA shell for unmatched non-API
  paths.
- `src/application/` assembles API/UI-facing DTOs from reusable services.
- `src/services/` coordinates import and dataset loading workflows.
- `src/models/` contains the canonical `PatentRecord` model and shared enums.
- `src/storage/` persists normalized records with direct `sqlite3`.
- `src/acquisition/` and `src/preprocessing/` handle file import and
  normalization boundaries.
- `src/features/`, `src/clustering/`, `src/insights/`, `src/optimization/`, and
  `src/visualization/` contain the analysis workflow.

## Canonical Record

`PatentRecord` is the canonical application model used across import, storage,
feature extraction, clustering, similarity mapping, insights, and graph
visualization.

`PatentRecord.analysis_id` is the stable analysis identifier used to distinguish
records across sources. It remains source-aware.

## Analysis Flow

1. CSV/JSON import or canonical corpus loading
2. normalization into canonical `PatentRecord` objects
3. SQLite persistence
4. keyword-evidence preparation
5. standard technology grouping
6. related-patent mapping
7. overlap signal and candidate application-area suggestions
8. dataset insights
9. patent map / graph data preparation
10. optional Genetic Algorithm grouping optimization
11. FastAPI response assembly
12. React presentation

## Current Technical Boundaries

- React + Vite + TypeScript is the UI surface.
- FastAPI is the backend/API layer.
- SQLite is the local runtime persistence layer.
- TF-IDF is the implemented text feature method.
- KMeans is the implemented standard grouping method.
- The Genetic Algorithm optimizes grouping configuration using grouping-quality
  scoring.
- PSO is not implemented.
- There is no ORM, embeddings pipeline, LLM call path, live patent-office API
  client, or exhaustive official source coverage in this repository.
- EPO, USPTO, and TURKPATENT/TPO labels describe source authority for the
  curated source-labeled corpus, not live integrations.

## Safe Interpretation Boundary

The application provides exploratory patent intelligence, relationship strength,
overlap signal, candidate application areas, optimized grouping, and corpus
coverage views. These are reading aids for the current curated corpus. They do
not provide legal or commercial decisions, and they do not represent exhaustive
official source coverage.

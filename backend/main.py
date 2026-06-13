"""FastAPI application entrypoint.

Run locally with::

    python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

Then visit:
    http://127.0.0.1:8000/health
    http://127.0.0.1:8000/docs

When ``frontend/dist`` exists (after ``npm run build`` inside ``frontend/``),
the same FastAPI process also serves the built React app and its client-side
routes from ``http://127.0.0.1:8000/``.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import (
    advanced_ai,
    analytics,
    data_sources,
    health,
    insights,
    landscape,
    patents,
)
from backend.core.config import BackendConfig, get_backend_config
from backend.core.static_frontend import configure_static_frontend


def create_app(config: BackendConfig | None = None) -> FastAPI:
    """Application factory used by uvicorn and the test client."""
    backend_config = config or get_backend_config()
    app = FastAPI(
        title=backend_config.api_title,
        description=backend_config.api_description,
        version=backend_config.api_version,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(backend_config.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(patents.router)
    app.include_router(landscape.router)
    app.include_router(insights.router)
    app.include_router(analytics.router)
    app.include_router(advanced_ai.router)
    app.include_router(data_sources.router)
    # Static frontend serving is registered last so concrete API/docs routes
    # take precedence over the SPA catch-all.
    configure_static_frontend(app, backend_config.frontend_dist_dir)
    return app


app = create_app()

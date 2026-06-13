"""Serve the built React frontend from FastAPI for single-app local runs.

Behavior:

- If ``frontend/dist`` exists, FastAPI mounts ``/assets`` (Vite's bundled
  output) and registers a catch-all route that returns ``index.html`` for
  any other path. That lets React Router handle client-side routes such as
  ``/patents/USPTO%3AUS-SENSOR-1`` even on hard refresh.
- Paths that belong to the API surface — ``/api/...``, ``/assets/...``,
  static-files internals — never produce ``index.html``. ``/api/<unknown>``
  returns a JSON 404, matching the existing API contract.
- Specifically declared routes (``/health``, ``/docs``, ``/openapi.json``,
  ``/redoc``) match before the catch-all, so they keep working unchanged.
- When ``frontend/dist`` is absent, this module is a no-op and the backend
  continues to serve only the JSON API + docs.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Path prefixes the SPA fallback must never hijack. /docs, /openapi.json,
# /redoc, and /health are already concrete routes, so they outrank the
# catch-all by virtue of route ordering; we list ``api/`` and ``assets/``
# explicitly because unknown sub-paths under those prefixes must keep their
# API/static semantics instead of returning the SPA shell.
_RESERVED_PREFIXES: tuple[str, ...] = ("api/", "assets/")


def configure_static_frontend(app: FastAPI, dist_dir: Path | None) -> bool:
    """Wire static frontend serving onto ``app`` if ``dist_dir`` is present.

    Returns True when SPA serving was configured, False otherwise. The
    function is idempotent enough for tests: each call sets up new routes
    on the given app instance.
    """
    if dist_dir is None or not dist_dir.is_dir():
        return False

    index_file = dist_dir / "index.html"
    if not index_file.is_file():
        return False

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="frontend-assets",
        )

    dist_root = dist_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        # Never let the SPA shell satisfy API or static-asset requests.
        for prefix in _RESERVED_PREFIXES:
            if full_path == prefix.rstrip("/") or full_path.startswith(prefix):
                raise HTTPException(status_code=404, detail="Not Found")

        # If the request maps to a real file in dist (favicon.ico, vite.svg),
        # serve it directly. Guard against path traversal.
        if full_path:
            candidate = (dist_dir / full_path).resolve()
            try:
                candidate.relative_to(dist_root)
            except ValueError:
                raise HTTPException(status_code=404, detail="Not Found") from None
            if candidate.is_file():
                return FileResponse(candidate)

        # Otherwise serve the SPA shell so React Router can pick up the route.
        return FileResponse(index_file)

    return True

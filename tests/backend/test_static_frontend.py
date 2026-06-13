"""Tests for FastAPI single-app local mode (built React app + JSON API)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.core.config import BackendConfig
from backend.main import create_app

_FAKE_INDEX_HTML = (
    "<!doctype html><html><head><title>FAKE-SPA</title></head>"
    "<body><div id='root'></div></body></html>"
)
_FAKE_CSS = "body { background: #fff; }"
_FAKE_FAVICON = b"\x89PNG\r\n\x1a\nFAKE-FAVICON"


def _write_fake_dist(dist_dir: Path) -> None:
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text(_FAKE_INDEX_HTML, encoding="utf-8")
    assets = dist_dir / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "main.css").write_text(_FAKE_CSS, encoding="utf-8")
    (dist_dir / "favicon.ico").write_bytes(_FAKE_FAVICON)


@pytest.fixture()
def fake_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "frontend_dist"
    _write_fake_dist(dist)
    return dist


def _build_client(frontend_dist_dir: Path | None) -> TestClient:
    config = BackendConfig(frontend_dist_dir=frontend_dist_dir)
    return TestClient(create_app(config=config))


def test_app_starts_without_dist() -> None:
    with _build_client(None) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        # Unknown API paths must remain 404 JSON, not get a SPA shell.
        api_missing = client.get("/api/patents/does-not-exist-x")
        assert api_missing.status_code == 404
        assert api_missing.headers["content-type"].startswith("application/json")

        # Without a built frontend, the root path has no handler.
        root = client.get("/")
        assert root.status_code == 404


def test_index_served_when_dist_present(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "FAKE-SPA" in response.text


def test_spa_fallback_for_client_routes(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        # React Router routes resolve to the SPA shell on direct/refresh hits.
        for path in (
            "/insights",
            "/landscape",
            "/advanced-ai",
            "/data-sources",
            "/patents/USPTO%3AUS-SENSOR-1",
        ):
            response = client.get(path)
            assert (
                response.status_code == 200
            ), f"Path {path} returned {response.status_code}"
            assert (
                "FAKE-SPA" in response.text
            ), f"Path {path} did not return the SPA shell"


def test_assets_served_from_dist(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        response = client.get("/assets/main.css")
        assert response.status_code == 200
        assert "background" in response.text

        # Unknown assets must 404, not fall back to the SPA shell.
        missing = client.get("/assets/nope-not-here.css")
        assert missing.status_code == 404


def test_direct_dist_file_served(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.content == _FAKE_FAVICON


def test_api_404_not_intercepted_when_dist_present(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        response = client.get("/api/this-route-does-not-exist")
        assert response.status_code == 404
        # JSON body, not HTML index page.
        assert response.headers["content-type"].startswith("application/json")
        assert "FAKE-SPA" not in response.text


def test_health_still_works_with_dist(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"


def test_docs_and_openapi_still_work_with_dist(fake_dist: Path) -> None:
    with _build_client(fake_dist) as client:
        docs = client.get("/docs")
        assert docs.status_code == 200
        assert "swagger" in docs.text.lower() or "openapi" in docs.text.lower()

        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        payload = openapi.json()
        assert payload.get("openapi", "").startswith("3.")

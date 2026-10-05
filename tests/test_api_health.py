"""API tests: health endpoint."""

import cafe_finder
from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_status():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "cafe-finder"


def test_health_version_matches_package():
    body = client.get("/api/health").json()
    assert body["version"] == cafe_finder.__version__


def test_health_reports_dataset_availability():
    body = client.get("/api/health").json()
    assert body["dataset"]["available"] is True
    assert body["dataset"]["records"] == 33


def test_openapi_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/health" in paths
    assert "/api/cafes" in paths
    assert "/api/search" in paths


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200

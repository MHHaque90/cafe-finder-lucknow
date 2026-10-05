"""API tests: structured analytics."""

from api.dependencies import load_dataset
from api.main import app
from cafe_finder.visualize import (
    calculate_completeness,
    prepare_coordinates,
    prepare_cuisine_counts,
)
from fastapi.testclient import TestClient

client = TestClient(app)


def test_analytics_schema():
    body = client.get("/api/analytics").json()
    assert set(body.keys()) == {"overview", "cuisine", "completeness", "coordinates"}
    assert set(body["overview"].keys()) == {"total_records", "columns"}
    assert set(body["coordinates"].keys()) == {"count", "latitudes", "longitudes", "bounds"}


def test_analytics_overview_consistent():
    body = client.get("/api/analytics").json()
    assert body["overview"]["total_records"] == 33
    assert len(body["overview"]["columns"]) == 13


def test_analytics_cuisine_consistent_with_domain():
    df = load_dataset()
    expected = prepare_cuisine_counts(df)
    body = client.get("/api/analytics").json()
    actual = {entry["tag"]: entry["count"] for entry in body["cuisine"]}
    assert actual == {str(tag): int(count) for tag, count in expected.items()}
    counts = [entry["count"] for entry in body["cuisine"]]
    assert counts == sorted(counts, reverse=True)


def test_analytics_completeness_consistent_with_domain():
    df = load_dataset()
    expected = calculate_completeness(df)
    body = client.get("/api/analytics").json()
    assert body["completeness"] == {str(k): float(v) for k, v in expected.items()}


def test_analytics_coordinates_consistent_with_domain():
    df = load_dataset()
    expected_lats, expected_lons = prepare_coordinates(df)
    body = client.get("/api/analytics").json()
    coords = body["coordinates"]
    assert coords["count"] == len(expected_lats) == len(expected_lons)
    assert coords["latitudes"] == [float(v) for v in expected_lats]
    assert coords["longitudes"] == [float(v) for v in expected_lons]
    if coords["count"]:
        bounds = coords["bounds"]
        assert bounds["min_latitude"] == min(expected_lats)
        assert bounds["max_latitude"] == max(expected_lats)
        assert bounds["min_longitude"] == min(expected_lons)
        assert bounds["max_longitude"] == max(expected_lons)

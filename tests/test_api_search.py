"""API tests: search pipeline (filters, distance, radius, ranking, sorting)."""

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

LAT = 26.8467
LON = 80.9462


def _search(**params):
    response = client.get("/api/search", params=params)
    assert response.status_code == 200
    return response.json()


def test_search_no_filters_returns_all_sorted_by_name():
    from api.dependencies import load_dataset
    from cafe_finder.search import sort_results

    body = _search()
    assert body["count"] == 33
    expected_ids = list(sort_results(load_dataset(), "name")["osm_id"])
    assert [record["osm_id"] for record in body["results"]] == expected_ids


def test_search_name_filter():
    body = _search(name="coffee")
    assert body["count"] >= 1
    assert all("coffee" in (record["name"] or "").lower() for record in body["results"])


def test_search_cuisine_filter():
    body = _search(cuisine="coffee_shop")
    assert body["count"] >= 1
    for record in body["results"]:
        tags = [tag.strip().lower() for tag in (record["cuisine"] or "").split(";")]
        assert "coffee_shop" in tags


def test_search_location_adds_distances():
    body = _search(lat=LAT, lon=LON)
    assert body["count"] == 33
    assert all(
        record["distance_km"] is not None and record["distance_km"] >= 0
        for record in body["results"]
    )


def test_search_location_defaults_to_distance_order():
    body = _search(lat=LAT, lon=LON)
    distances = [record["distance_km"] for record in body["results"]]
    assert distances == sorted(distances)


def test_search_radius_filters():
    body = _search(lat=LAT, lon=LON, radius=3)
    assert 0 < body["count"] < 33
    assert all(record["distance_km"] <= 3 for record in body["results"])


def test_search_ranking_fields_and_reasons():
    body = _search(cuisine="coffee_shop", sort_by="score")
    assert body["count"] >= 1
    first = body["results"][0]
    assert first["score_total"] >= 30
    assert first["score_cuisine"] == 30
    assert first["score_reasons"]
    assert any("coffee_shop" in reason for reason in first["score_reasons"])


def test_search_score_sort_descending():
    body = _search(sort_by="score")
    totals = [record["score_total"] for record in body["results"]]
    assert totals == sorted(totals, reverse=True)


def test_search_explicit_distance_sort():
    body = _search(lat=LAT, lon=LON, sort_by="distance")
    distances = [record["distance_km"] for record in body["results"]]
    assert distances == sorted(distances)


def test_search_deterministic_repeated_calls():
    params = {"cuisine": "coffee_shop", "lat": LAT, "lon": LON, "radius": 5, "sort_by": "score"}
    first = client.get("/api/search", params=params).json()
    second = client.get("/api/search", params=params).json()
    assert first == second


def test_search_lat_without_lon_rejected():
    response = client.get("/api/search", params={"lat": LAT})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_search_lon_without_lat_rejected():
    response = client.get("/api/search", params={"lon": LON})
    assert response.status_code == 400


def test_search_radius_without_location_rejected():
    response = client.get("/api/search", params={"radius": 3})
    assert response.status_code == 400


def test_search_negative_radius_rejected():
    response = client.get("/api/search", params={"lat": LAT, "lon": LON, "radius": -1})
    assert response.status_code == 400


def test_search_invalid_latitude_rejected():
    response = client.get("/api/search", params={"lat": 200, "lon": LON})
    assert response.status_code == 400


def test_search_invalid_longitude_rejected():
    response = client.get("/api/search", params={"lat": LAT, "lon": 200})
    assert response.status_code == 400


def test_search_distance_sort_without_location_rejected():
    response = client.get("/api/search", params={"sort_by": "distance"})
    assert response.status_code == 400


def test_search_invalid_sort_rejected():
    response = client.get("/api/search", params={"sort_by": "rating"})
    assert response.status_code == 400


def test_search_no_traceback_leakage():
    for params in ({"lat": 200, "lon": LON}, {"sort_by": "rating"}, {"radius": -5}):
        body = client.get("/api/search", params=params).json()
        assert "Traceback" not in str(body)

"""API tests: cafe listing, filtering, and detail lookup."""

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_list_cafes_returns_all_records():
    body = client.get("/api/cafes").json()
    assert body["count"] == 33
    assert len(body["results"]) == 33
    assert all(record["osm_id"] for record in body["results"])


def test_list_cafes_name_filter():
    body = client.get("/api/cafes", params={"name": "coffee"}).json()
    assert body["count"] >= 1
    assert all("coffee" in (record["name"] or "").lower() for record in body["results"])


def test_list_cafes_cuisine_filter_exact_tag():
    body = client.get("/api/cafes", params={"cuisine": "coffee_shop"}).json()
    assert body["count"] >= 1
    for record in body["results"]:
        tags = [tag.strip().lower() for tag in (record["cuisine"] or "").split(";")]
        assert "coffee_shop" in tags


def test_cuisine_filter_is_not_substring():
    exact = client.get("/api/cafes", params={"cuisine": "coffee_shop"}).json()["count"]
    partial = client.get("/api/cafes", params={"cuisine": "coffee"}).json()["count"]
    assert partial == 0
    assert exact > 0


def test_list_cafes_combined_filters_use_and():
    body = client.get(
        "/api/cafes", params={"cuisine": "coffee_shop", "has_website": "true"}
    ).json()
    for record in body["results"]:
        tags = [tag.strip().lower() for tag in (record["cuisine"] or "").split(";")]
        assert "coffee_shop" in tags
        assert record["website"]


def test_list_cafes_website_filter():
    body = client.get("/api/cafes", params={"has_website": "true"}).json()
    assert all(record["website"] for record in body["results"])


def test_list_cafes_phone_filter():
    body = client.get("/api/cafes", params={"has_phone": "true"}).json()
    assert all(record["phone"] for record in body["results"])


def test_list_cafes_opening_hours_filter():
    body = client.get("/api/cafes", params={"has_opening_hours": "true"}).json()
    assert all(record["opening_hours"] for record in body["results"])


def test_list_cafes_empty_name_rejected():
    response = client.get("/api/cafes", params={"name": "   "})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_get_cafe_known_id():
    known = client.get("/api/cafes").json()["results"][0]["osm_id"]
    response = client.get(f"/api/cafes/{known}")
    assert response.status_code == 200
    assert response.json()["osm_id"] == known


def test_get_cafe_unknown_id_returns_404():
    response = client.get("/api/cafes/node0000000000")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_cafe_does_not_substitute_name_match():
    first = client.get("/api/cafes").json()["results"][0]
    response = client.get("/api/cafes/definitely-not-an-osm-id")
    assert response.status_code == 404
    assert first["osm_id"] != "definitely-not-an-osm-id"


def test_get_cafe_without_cuisine_has_no_scores():
    known = client.get("/api/cafes").json()["results"][0]["osm_id"]
    record = client.get(f"/api/cafes/{known}").json()
    assert record["score_total"] is None
    assert record["score_reasons"] is None


def test_get_cafe_with_cuisine_uses_rank_cafes():
    from api.serializers import serialize_records
    from cafe_finder.ranking import rank_cafes
    from api.dependencies import load_dataset

    known = client.get("/api/cafes").json()["results"][0]["osm_id"]
    df = load_dataset()
    expected = serialize_records(
        rank_cafes(df[df["osm_id"] == known].head(1), "coffee_shop")
    )[0]
    record = client.get(f"/api/cafes/{known}", params={"cuisine": "coffee_shop"}).json()
    assert record["score_total"] == expected["score_total"]
    assert record["score_cuisine"] == expected["score_cuisine"]
    assert record["score_reasons"] == expected["score_reasons"]


def test_cafe_records_have_expected_fields():
    record = client.get("/api/cafes").json()["results"][0]
    for field in (
        "osm_id", "name", "latitude", "longitude", "street", "housenumber",
        "city", "postcode", "cuisine", "opening_hours", "website", "phone", "source",
    ):
        assert field in record


def test_missing_values_are_null_not_strings():
    body = client.get("/api/cafes").json()
    nulls_seen = [
        record for record in body["results"] if record["website"] is None
    ]
    assert nulls_seen, "dataset is expected to contain missing websites"
    for record in body["results"]:
        assert record["website"] != ""

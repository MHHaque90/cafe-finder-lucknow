"""API parity tests: endpoints must match domain functions exactly.

For each representative query the test runs the existing domain
functions directly and the HTTP endpoint, then compares semantic
results (normalizing only serialization differences).
"""

from api.dependencies import load_dataset
from api.main import app
from api.serializers import serialize_records
from cafe_finder.distance import calculate_distances
from cafe_finder.ranking import rank_cafes
from cafe_finder.search import apply_filters, sort_results
from fastapi.testclient import TestClient

client = TestClient(app)
LAT = 26.8467
LON = 80.9462


def _domain_search(name=None, cuisine=None, has_website=False, has_phone=False,
                   has_opening_hours=False, lat=None, lon=None, radius=None,
                   sort_by="name"):
    df = load_dataset()
    results = apply_filters(
        df, name_query=name, cuisine=cuisine, has_website=has_website,
        has_phone=has_phone, has_opening_hours=has_opening_hours,
    )
    has_location = lat is not None and lon is not None
    if has_location:
        results = calculate_distances(results, lat, lon)
        if sort_by == "distance" or (sort_by == "name" and has_location):
            results = results.sort_values(by="distance_km", na_position="last").copy()
        if radius is not None:
            results = results[results["distance_km"] <= radius].copy()
    if sort_by == "score":
        from cafe_finder.search import is_value_present

        results = rank_cafes(results, cuisine)
        results["_sort_name"] = results["name"].apply(
            lambda x: str(x).strip().lower() if is_value_present(x) else ""
        )
        results["_sort_osm_id"] = results["osm_id"].apply(
            lambda x: str(x).strip().lower() if is_value_present(x) else ""
        )
        results = results.sort_values(
            by=["score_total", "_sort_name", "_sort_osm_id"],
            ascending=[False, True, True],
            na_position="last",
        ).copy()
        results = results.drop(columns=["_sort_name", "_sort_osm_id"])
    if not has_location and sort_by in ["name", "latitude", "longitude"]:
        results = sort_results(results, sort_by)
    return results


def _api_records(params):
    body = client.get("/api/search", params=params).json()
    return body


def _assert_same_order(domain_df, api_body):
    expected_ids = list(domain_df["osm_id"])
    actual_ids = [record["osm_id"] for record in api_body["results"]]
    assert actual_ids == expected_ids
    assert api_body["count"] == len(expected_ids)


def test_parity_case_a_no_filters():
    _assert_same_order(_domain_search(), _api_records({}))


def test_parity_case_b_cuisine():
    _assert_same_order(
        _domain_search(cuisine="coffee_shop"), _api_records({"cuisine": "coffee_shop"})
    )


def test_parity_case_c_name_filter():
    _assert_same_order(
        _domain_search(name="cafe"), _api_records({"name": "cafe"})
    )


def test_parity_case_d_website_filter():
    _assert_same_order(
        _domain_search(has_website=True), _api_records({"has_website": "true"})
    )


def test_parity_case_e_location_radius():
    params = {"lat": LAT, "lon": LON, "radius": 3}
    domain = _domain_search(lat=LAT, lon=LON, radius=3)
    _assert_same_order(domain, _api_records(params))
    api_distances = [r["distance_km"] for r in _api_records(params)["results"]]
    domain_distances = [
        None if v is None else float(v) for v in domain["distance_km"].tolist()
    ]
    assert api_distances == domain_distances


def test_parity_case_f_cuisine_distance_ranking():
    params = {"cuisine": "coffee_shop", "lat": LAT, "lon": LON,
              "radius": 5, "sort_by": "score"}
    domain = _domain_search(cuisine="coffee_shop", lat=LAT, lon=LON, radius=5, sort_by="score")
    body = _api_records(params)
    _assert_same_order(domain, body)
    expected_totals = [int(v) for v in domain["score_total"].tolist()]
    assert [r["score_total"] for r in body["results"]] == expected_totals
    expected_first_reasons = list(domain.iloc[0]["score_reasons"])
    assert body["results"][0]["score_reasons"] == expected_first_reasons


def test_parity_case_g_score_sorting():
    domain = _domain_search(sort_by="score")
    _assert_same_order(domain, _api_records({"sort_by": "score"}))


def test_parity_case_h_unknown_osm_id():
    response = client.get("/api/cafes/does-not-exist-123")
    assert response.status_code == 404


def test_parity_cafes_endpoint_matches_apply_filters():
    df = load_dataset()
    domain = apply_filters(df, name_query=None, cuisine="coffee_shop",
                           has_website=False, has_phone=False, has_opening_hours=False)
    from cafe_finder.search import sort_results as domain_sort

    domain = domain_sort(domain, "name")
    body = client.get("/api/cafes", params={"cuisine": "coffee_shop"}).json()
    assert [r["osm_id"] for r in body["results"]] == list(domain["osm_id"])


def test_parity_serialized_values_match_domain():
    df = load_dataset()
    expected = serialize_records(df.head(3))
    body = client.get("/api/cafes").json()
    by_id = {r["osm_id"]: r for r in body["results"]}
    canonical = [
        "osm_id", "name", "latitude", "longitude", "street", "housenumber",
        "city", "postcode", "cuisine", "opening_hours", "website", "phone", "source",
    ]
    for record in expected:
        actual = by_id[record["osm_id"]]
        assert {k: actual[k] for k in canonical} == {
            k: record[k] for k in canonical
        }

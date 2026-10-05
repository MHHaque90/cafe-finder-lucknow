"""API tests: structured data quality (no aggregate score by design)."""

from api.dependencies import load_dataset
from api.main import app
from cafe_finder.quality import (
    generate_provenance,
    generate_quality_report,
    generate_record_quality_flags,
)
from fastapi.testclient import TestClient

client = TestClient(app)


def test_quality_schema():
    body = client.get("/api/quality").json()
    assert set(body.keys()) == {"report", "provenance", "records"}
    assert len(body["records"]) == 33
    assert set(body["records"][0].keys()) == {
        "osm_id", "quality_flags", "quality_issue_count",
    }


def test_quality_has_no_aggregate_score():
    body = client.get("/api/quality").json()
    flattened = str(body).lower()
    assert "quality_score" not in flattened
    assert "overall_score" not in flattened


def test_quality_report_consistent_with_domain():
    df = load_dataset()
    expected = generate_quality_report(df)
    body = client.get("/api/quality").json()
    assert body["report"]["total_records"] == expected["total_records"]
    assert (
        body["report"]["valid_coordinate_records"]
        == expected["valid_coordinate_records"]
    )
    assert (
        body["report"]["duplicate_osm_id_records"]
        == expected["duplicate_osm_id_records"]
    )
    assert body["report"]["field_completeness"] == expected["field_completeness"]


def test_quality_provenance_source_and_method():
    body = client.get("/api/quality").json()
    provenance = body["provenance"]
    assert provenance["source"] == "OpenStreetMap"
    assert provenance["retrieval_method"] == "Overpass API"
    assert provenance["record_count"] == 33
    assert provenance["retrieved_at"]


def test_quality_flags_consistent_with_domain():
    df = load_dataset()
    expected = generate_record_quality_flags(df)
    body = client.get("/api/quality").json()
    by_id = {record["osm_id"]: record for record in body["records"]}
    for _, row in expected.iterrows():
        flags = by_id[row["osm_id"]]
        assert flags["quality_flags"] == list(row["quality_flags"])
        assert flags["quality_issue_count"] == int(row["quality_issue_count"])

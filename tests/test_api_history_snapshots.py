"""Happy-path API tests for governance endpoints with real snapshots.

Builds two complete synthetic snapshots in temporary directories (using
the repository's own snapshot/manifest recipe) and verifies that the
history, detail, comparison, integrity, and lineage endpoints expose
them exactly as the domain computes them. No production snapshot data
is created or modified.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from cafe_finder import integrity, manifest, schema, snapshot

client = TestClient(app)

BASELINE_ID = "2026-01-01T000000Z"
TARGET_ID = "2026-02-01T000000Z"
RETRIEVED_AT = "2026-02-01T00:00:00Z"


def _record(osm_id: str, name: str) -> dict:
    return {
        "osm_id": osm_id,
        "name": name,
        "latitude": 26.85,
        "longitude": 80.95,
        "street": "Test Street",
        "housenumber": "1",
        "city": "Lucknow",
        "postcode": "226001",
        "cuisine": "cafe",
        "opening_hours": "08:00-22:00",
        "website": "http://example.com",
        "phone": "+91-1234567890",
        "source": "OpenStreetMap",
    }


@pytest.fixture
def two_snapshots(tmp_path: Path) -> dict:
    """Create two complete snapshots and point domain dirs at them."""
    raw = tmp_path / "raw" / "snapshots"
    processed = tmp_path / "processed" / "snapshots"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)

    orig_raw = snapshot.SNAPSHOTS_RAW_DIR
    orig_proc = snapshot.SNAPSHOTS_PROCESSED_DIR
    orig_proc_csv = integrity.PROCESSED_CSV_PATH
    snapshot.SNAPSHOTS_RAW_DIR = raw
    snapshot.SNAPSHOTS_PROCESSED_DIR = processed
    integrity.PROCESSED_CSV_PATH = tmp_path / "processed" / "lucknow_cafes.csv"

    baseline_df = pd.DataFrame([_record("node1", "Cafe One"), _record("node2", "Cafe Two")])
    target_df = pd.DataFrame(
        [_record("node2", "Cafe Two Updated"), _record("node3", "Cafe Three")]
    )
    for sid, df in ((BASELINE_ID, baseline_df), (TARGET_ID, target_df)):
        snapshot_dir = raw / sid
        processed_snapshot_dir = processed / sid
        snapshot_dir.mkdir(parents=True)
        processed_snapshot_dir.mkdir(parents=True)
        raw_file = snapshot_dir / "raw.json"
        raw_file.write_text("[]")
        processed_file = processed_snapshot_dir / "cafes.csv"
        df.to_csv(processed_file, index=False)
        metadata = snapshot.generate_metadata(
            snapshot_id=sid,
            retrieved_at_utc=RETRIEVED_AT,
            record_count=len(df),
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
        )
        (snapshot_dir / "metadata.json").write_text(json.dumps(metadata))
        artifacts = [
            manifest.compute_artifact_entry(raw_file, str(raw_file)),
            manifest.compute_artifact_entry(processed_file, str(processed_file)),
        ]
        draft = manifest.build_manifest_draft(
            snapshot_id=sid,
            started_at_utc=RETRIEVED_AT,
            retrieved_at_utc=RETRIEVED_AT,
            endpoint="https://overpass-api.de/api/interpreter",
            query="[out:json];",
            record_count=len(df),
            artifacts=artifacts,
            schema_result={},
        )
        manifest.write_manifest(
            manifest.build_manifest(draft, RETRIEVED_AT), snapshot_dir / "manifest.json"
        )

    yield {"baseline": baseline_df, "target": target_df}

    snapshot.SNAPSHOTS_RAW_DIR = orig_raw
    snapshot.SNAPSHOTS_PROCESSED_DIR = orig_proc
    integrity.PROCESSED_CSV_PATH = orig_proc_csv


def test_history_lists_two_snapshots_newest_first(two_snapshots):
    response = client.get("/api/history")
    assert response.status_code == 200
    body = response.json()
    assert [s["snapshot_id"] for s in body["snapshots"]] == [TARGET_ID, BASELINE_ID]
    assert body["snapshots"][0]["record_count"] == 2
    assert body["snapshots"][0]["source"] == "OpenStreetMap"
    summary = body["summary"]
    assert summary["snapshots_analyzed"] == 2
    assert summary["unique_cafes"] == 3


def test_snapshot_detail_reports_passed_integrity(two_snapshots):
    response = client.get(f"/api/history/{TARGET_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["snapshot_id"] == TARGET_ID
    assert body["metadata"]["record_count"] == 2
    assert body["integrity_status"] == "PASSED"
    assert body["integrity_errors"] == []


def test_compare_reports_added_removed_modified(two_snapshots):
    response = client.get(
        "/api/history/compare", params={"baseline": BASELINE_ID, "target": TARGET_ID}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["baseline"] == BASELINE_ID
    assert body["target"] == TARGET_ID
    assert body["old_record_count"] == 2
    assert body["new_record_count"] == 2
    assert [row["osm_id"] for row in body["added"]] == ["node3"]
    assert [row["osm_id"] for row in body["removed"]] == ["node1"]
    assert [entry["osm_id"] for entry in body["modified"]] == ["node2"]
    name_change = body["modified"][0]["changes"]
    assert {"field": "name", "old": "Cafe Two", "new": "Cafe Two Updated"} in name_change
    assert body["unchanged"] == []
    assert any(
        change["field"] == "name" for change in body["field_changes"]
    )


def test_compare_parity_with_domain(two_snapshots):
    from api.serializers import to_jsonable
    from cafe_finder.compare import compare_datasets

    expected = compare_datasets(two_snapshots["baseline"], two_snapshots["target"])
    response = client.get(
        "/api/history/compare", params={"baseline": BASELINE_ID, "target": TARGET_ID}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["added"] == [to_jsonable(row.to_dict()) for row in expected["added"]]
    assert body["removed"] == [to_jsonable(row.to_dict()) for row in expected["removed"]]
    assert body["modified"] == to_jsonable(expected["modified"])
    assert body["unchanged"] == to_jsonable(expected["unchanged"])
    assert body["field_changes"] == to_jsonable(expected["field_changes"])


def test_integrity_passes_for_latest_snapshot(two_snapshots):
    response = client.get("/api/integrity")
    assert response.status_code == 200
    snapshot_integrity = response.json()["snapshot_integrity"]
    assert snapshot_integrity["snapshot_id"] == TARGET_ID
    assert snapshot_integrity["status"] == "PASSED"
    assert snapshot_integrity["errors"] == []


def test_lineage_available_with_snapshots(two_snapshots):
    response = client.get("/api/lineage")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    report = body["report"]
    assert report["snapshots_analyzed"] == 2
    assert report["snapshot_ids"] == [BASELINE_ID, TARGET_ID]
    assert report["source"] == "OpenStreetMap"
    assert body["reason"] is None

"""API tests for the integrity endpoint.

Real repository state: no snapshots exist (NO_SNAPSHOTS), the live
dataset fails strict schema validation (missing names, numeric
postcode/phone), and the dataset artifact exists and is readable.
The endpoint must report all three truthfully, and match the domain
functions exactly.
"""

from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import load_dataset
from api.serializers import to_jsonable
from cafe_finder.config import DEFAULT_CSV_PATH
from cafe_finder.integrity import verify_artifact, verify_latest
from cafe_finder.schema import validate_schema

client = TestClient(app)


def test_integrity_reports_unavailable_snapshot_status_honestly():
    response = client.get("/api/integrity")
    assert response.status_code == 200
    body = response.json()
    snapshot_integrity = body["snapshot_integrity"]
    assert snapshot_integrity["status"] == "NO_SNAPSHOTS"
    assert snapshot_integrity["snapshot_id"] is None
    assert snapshot_integrity["errors"] == ["No snapshot directories exist"]


def test_integrity_reports_real_schema_result():
    response = client.get("/api/integrity")
    assert response.status_code == 200
    schema = response.json()["schema"]
    # The live dataset genuinely fails strict schema validation.
    assert schema["valid"] is False
    assert schema["schema_version"] == 1
    assert schema["missing_columns"] == []
    assert "name" in schema["invalid_types"]


def test_integrity_reports_readable_artifact():
    response = client.get("/api/integrity")
    assert response.status_code == 200
    artifact = response.json()["artifact"]
    assert artifact["exists"] is True
    assert artifact["readable"] is True
    assert artifact["valid"] is True
    assert artifact["error"] is None
    assert artifact["sha256_expected"] is None
    assert artifact["size_expected"] is None


def test_integrity_parity_with_domain():
    from api.schemas import SnapshotIntegrity

    df = load_dataset()
    response = client.get("/api/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_integrity"] == SnapshotIntegrity(
        **to_jsonable(verify_latest())
    ).model_dump()
    assert body["schema"] == to_jsonable(validate_schema(df))
    assert body["artifact"] == to_jsonable(verify_artifact(DEFAULT_CSV_PATH, None, None))

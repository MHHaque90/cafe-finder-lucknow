"""API tests for the lineage endpoint.

Real repository state: no successful snapshots exist, so historical
lineage is unavailable. The endpoint must say so honestly instead of
inventing stages.
"""

from fastapi.testclient import TestClient

from api.main import app
from cafe_finder.lineage import LineageError, generate_lineage

client = TestClient(app)


def test_lineage_unavailable_without_snapshots():
    response = client.get("/api/lineage")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["report"] is None
    assert body["reason"] == (
        "No valid successful snapshots found; "
        "cannot establish historical-analysis lineage."
    )


def test_lineage_parity_with_domain():
    try:
        generate_lineage()
        domain_available = True
    except LineageError as exc:
        domain_available = False
        domain_reason = str(exc)
    response = client.get("/api/lineage")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is domain_available
    if domain_available:
        assert body["report"]["snapshots_analyzed"] >= 1
        assert body["reason"] is None
    else:
        assert body["report"] is None
        assert body["reason"] == domain_reason

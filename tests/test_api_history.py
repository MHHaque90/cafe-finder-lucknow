"""API tests for history, snapshot, and comparison endpoints.

All assertions run against real repository state: no snapshots exist on
disk, so the endpoints must report honest empty states. Parity checks
re-run the domain functions and compare full response bodies.
"""

from fastapi.testclient import TestClient

from api.main import app
from api.serializers import to_jsonable
from cafe_finder.history import summarize_history
from cafe_finder.snapshot import list_snapshots

client = TestClient(app)


def test_history_lists_no_snapshots_honestly():
    response = client.get("/api/history")
    assert response.status_code == 200
    body = response.json()
    assert body["snapshots"] == []
    summary = body["summary"]
    assert summary["snapshots_analyzed"] == 0
    assert summary["snapshot_ids"] == []
    assert summary["first_snapshot"] is None
    assert summary["latest_snapshot"] is None


def test_history_parity_with_domain():
    snapshots = list_snapshots()
    assert snapshots == []
    response = client.get("/api/history")
    assert response.status_code == 200
    body = response.json()
    assert body["snapshots"] == [to_jsonable(meta) for meta in snapshots]
    assert body["summary"] == to_jsonable(summarize_history(snapshots))


def test_unknown_snapshot_returns_404_without_traceback():
    response = client.get("/api/history/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert body == {"detail": "Unknown snapshot: nonexistent"}
    assert "Traceback" not in str(body)


def test_compare_same_snapshot_returns_400():
    response = client.get("/api/history/compare", params={"baseline": "a", "target": "a"})
    assert response.status_code == 400
    assert response.json() == {"detail": "baseline and target must be different snapshots"}


def test_compare_unknown_snapshot_returns_404():
    response = client.get("/api/history/compare", params={"baseline": "a", "target": "b"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown snapshot: a"}


def test_compare_requires_both_parameters():
    response = client.get("/api/history/compare", params={"baseline": "a"})
    assert response.status_code == 422

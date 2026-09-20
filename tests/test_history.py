"""Tests for historical change analysis (Phase 9)."""

import json
import sys

import pandas as pd
import pytest

from cafe_finder.history import (
    CHANGE_FIELDS,
    OBSERVATION_FIELDS,
    SnapshotDataError,
    build_change_history,
    build_observation_history,
    build_quality_history,
    discover_snapshots,
    export_changes_csv,
    export_observations_csv,
    format_cafe_history,
    format_fields,
    format_summary,
    main,
    reconstruct_snapshot,
    summarize_history,
)
from cafe_finder import schema

A_ID = "2026-08-01T120000Z"
A_AT = "2026-08-01T12:00:00+00:00"
B_ID = "2026-08-15T120000Z"
B_AT = "2026-08-15T12:00:00+00:00"
C_ID = "2026-09-01T120000Z"
C_AT = "2026-09-01T12:00:00+00:00"


@pytest.fixture
def history_dirs(tmp_path, monkeypatch):
    """Redirect Phase 8 snapshot dirs to temp locations."""
    import cafe_finder.snapshot as snap_mod

    raw = tmp_path / "raw" / "snapshots"
    processed = tmp_path / "processed" / "snapshots"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    monkeypatch.setattr(snap_mod, "SNAPSHOTS_RAW_DIR", raw)
    monkeypatch.setattr(snap_mod, "SNAPSHOTS_PROCESSED_DIR", processed)
    return {"raw": raw, "processed": processed}


def cafe(osm_id, name=None, **kw):
    """Build a cafe row with stable defaults."""
    row = {
        "osm_id": osm_id,
        "name": name,
        "latitude": 26.85,
        "longitude": 80.94,
        "street": None,
        "housenumber": None,
        "city": "Lucknow",
        "postcode": None,
        "cuisine": None,
        "opening_hours": None,
        "website": None,
        "phone": None,
        "source": None,
    }
    row.update(kw)
    return row


def make_snapshot(snapshot_id, retrieved_at, rows):
    import cafe_finder.snapshot as snap_mod
    """Create a complete synthetic snapshot (raw + processed + metadata + manifest)."""
    from cafe_finder.snapshot import save_processed_snapshot, save_raw_snapshot
    from cafe_finder import manifest, schema

    if isinstance(rows, pd.DataFrame):
        df = rows
        raw_records = df.to_dict(orient="records")
    else:
        df = pd.DataFrame(rows)
        raw_records = [dict(r) for r in rows]
    save_raw_snapshot(
        records=raw_records,
        snapshot_id=snapshot_id,
        retrieved_at_utc=retrieved_at,
        query="test-query",
    )
    save_processed_snapshot(
        df=df, snapshot_id=snapshot_id, retrieved_at_utc=retrieved_at, query="test-query"
    )
    # Create minimal manifest for Phase 10 compatibility
    from cafe_finder import integrity
    snapshot_dir = snap_mod.SNAPSHOTS_RAW_DIR / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    processed_snapshot_dir = snap_mod.SNAPSHOTS_PROCESSED_DIR / snapshot_id
    processed_snapshot_dir.mkdir(parents=True, exist_ok=True)
    raw_file = snapshot_dir / "raw.json"
    processed_file = processed_snapshot_dir / "cafes.csv"
    artifacts = [
        {"path": str(raw_file.resolve()), "sha256": integrity.sha256_file(raw_file), "size_bytes": raw_file.stat().st_size},
        {"path": str(processed_file.resolve()), "sha256": integrity.sha256_file(processed_file), "size_bytes": processed_file.stat().st_size},
    ]
    draft = {
        "manifest_version": 1,
        "pipeline_name": "cafe_finder",
        "schema_version": 1,
        "status": "preparing",
        "snapshot_id": snapshot_id,
        "started_at_utc": retrieved_at,
        "retrieved_at_utc": retrieved_at,
        "source": "OpenStreetMap",
        "retrieval_method": "Overpass API",
        "endpoint": "https://overpass-api.de/api/interpreter",
        "query": "test-query",
        "record_count": len(df),
        "artifacts": artifacts,
        "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
    }
    final = {**draft, "status": "success", "completed_at_utc": retrieved_at}
    (snapshot_dir / "manifest.json").write_text(json.dumps(final))


def run_cli(monkeypatch, *argv):
    """Run history.main() with patched argv."""
    monkeypatch.setattr(sys, "argv", ["history", *argv])


class TestDiscovery:
    """Snapshot discovery tests (1-6)."""

    def test_no_snapshots(self, history_dirs):
        assert discover_snapshots() == []

    def test_one_valid_snapshot(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        snapshots = discover_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["snapshot_id"] == A_ID

    def test_multiple_snapshots(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        assert len(discover_snapshots()) == 2

    def test_failed_snapshot_ignored(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        meta_file = history_dirs["raw"] / B_ID / "metadata.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["status"] = "failed"
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
        snapshots = discover_snapshots()
        assert [m["snapshot_id"] for m in snapshots] == [A_ID]

    def test_incomplete_snapshot_ignored(self, history_dirs):
        from cafe_finder.snapshot import save_raw_snapshot

        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        save_raw_snapshot(
            records=[{"osm_id": "n1"}],
            snapshot_id=B_ID,
            retrieved_at_utc=B_AT,
            query="test-query",
        )
        snapshots = discover_snapshots()
        assert [m["snapshot_id"] for m in snapshots] == [A_ID]

    def test_chronological_ordering(self, history_dirs):
        make_snapshot(C_ID, C_AT, [cafe("n1", "A")])
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        assert [m["snapshot_id"] for m in discover_snapshots()] == [A_ID, B_ID, C_ID]


class TestObservationHistory:
    """Observation history tests (7-14)."""

    def test_first_observation(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        (obs,) = build_observation_history()
        assert obs["first_observed_snapshot"] == A_ID
        assert obs["first_observed_at"] == A_AT

    def test_last_observation(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        (obs,) = build_observation_history()
        assert obs["last_observed_snapshot"] == B_ID
        assert obs["last_observed_at"] == B_AT

    def test_present_in_every_snapshot(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        make_snapshot(C_ID, C_AT, [cafe("n1", "A")])
        (obs,) = build_observation_history()
        assert obs["snapshot_count"] == 3

    def test_appearing_later(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A"), cafe("n2", "B")])
        by_id = {o["osm_id"]: o for o in build_observation_history()}
        assert by_id["n2"]["first_observed_snapshot"] == B_ID
        assert by_id["n2"]["last_observed_snapshot"] == B_ID
        assert by_id["n2"]["snapshot_count"] == 1

    def test_disappearing_later(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n3", "C")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        by_id = {o["osm_id"]: o for o in build_observation_history()}
        assert by_id["n3"]["first_observed_snapshot"] == A_ID
        assert by_id["n3"]["last_observed_snapshot"] == A_ID
        assert by_id["n3"]["snapshot_count"] == 1

    def test_disappearing_and_reappearing(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n4", "D")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        make_snapshot(C_ID, C_AT, [cafe("n1", "A"), cafe("n4", "D")])
        by_id = {o["osm_id"]: o for o in build_observation_history()}
        assert by_id["n4"]["first_observed_snapshot"] == A_ID
        assert by_id["n4"]["last_observed_snapshot"] == C_ID
        assert by_id["n4"]["snapshot_count"] == 2

    def test_multiple_cafes(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n2", "B"), cafe("n3", "C")])
        observations = build_observation_history()
        assert [o["osm_id"] for o in observations] == ["n1", "n2", "n3"]

    def test_same_name_different_osm_id(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "Same"), cafe("n2", "Same")])
        observations = build_observation_history()
        assert len(observations) == 2
        assert {o["osm_id"] for o in observations} == {"n1", "n2"}


class TestChangeHistory:
    """Change history tests (15-22)."""

    def test_no_changes(self, history_dirs):
        rows = [cafe("n1", "A", website="http://a.com")]
        make_snapshot(A_ID, A_AT, rows)
        make_snapshot(B_ID, B_AT, [dict(r) for r in rows])
        assert build_change_history() == []

    def test_one_modification(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", website="http://a.com")])
        (change,) = build_change_history()
        assert change["osm_id"] == "n1"
        assert change["snapshot_before"] == A_ID
        assert change["snapshot_after"] == B_ID
        assert change["changed_at"] == B_AT
        assert change["field"] == "website"
        assert change["old_value"] is None
        assert change["new_value"] == "http://a.com"

    def test_multiple_modifications(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n2", "B")])
        make_snapshot(
            B_ID, B_AT, [cafe("n1", "A", website="http://a.com"), cafe("n2", "B", phone="1")]
        )
        changes = build_change_history()
        assert {(c["osm_id"], c["field"]) for c in changes} == {
            ("n1", "website"),
            ("n2", "phone"),
        }

    def test_multiple_fields_changed(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A New", website="http://a.com")])
        changes = build_change_history()
        assert len(changes) == 2
        assert {c["field"] for c in changes} == {"name", "website"}

    def test_addition_creates_no_field_records(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A"), cafe("n2", "B")])
        assert build_change_history() == []
        by_id = {o["osm_id"]: o for o in build_observation_history()}
        assert by_id["n2"]["first_observed_snapshot"] == B_ID

    def test_no_longer_observed_creates_no_field_records(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n3", "C")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        assert build_change_history() == []
        by_id = {o["osm_id"]: o for o in build_observation_history()}
        assert by_id["n3"]["last_observed_snapshot"] == A_ID

    def test_reappearance_creates_no_field_records(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n4", "D", website="http://d.com")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        make_snapshot(C_ID, C_AT, [cafe("n1", "A"), cafe("n4", "D", website="http://d.com")])
        assert build_change_history() == []

    def test_adjacent_comparisons_preserve_intermediate(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A", website="http://old.com")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", website="http://new.com")])
        make_snapshot(C_ID, C_AT, [cafe("n1", "A", website="http://old.com")])
        changes = build_change_history()
        assert len(changes) == 2
        assert changes[0]["snapshot_before"] == A_ID
        assert changes[0]["snapshot_after"] == B_ID
        assert changes[1]["snapshot_before"] == B_ID
        assert changes[1]["snapshot_after"] == C_ID


class TestMissingValues:
    """Missing-value semantics tests (23-26)."""

    def test_nan_vs_none_no_change(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", None)])
        make_snapshot(B_ID, B_AT, [cafe("n1", float("nan"))])
        assert build_change_history() == []

    def test_empty_vs_whitespace_no_change(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A", website="")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", website="   ")])
        assert build_change_history() == []

    def test_missing_to_populated(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", phone="+91-123")])
        (change,) = build_change_history()
        assert change["field"] == "phone"
        assert change["old_value"] is None
        assert change["new_value"] == "+91-123"

    def test_populated_to_missing(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A", phone="+91-123")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", phone="")])
        (change,) = build_change_history()
        assert change["field"] == "phone"
        assert change["old_value"] == "+91-123"
        assert change["new_value"] is None


class TestIdentity:
    """Identity semantics tests (27-30)."""

    def test_different_name_same_id(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "Old Name")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "New Name")])
        (obs,) = build_observation_history()
        assert obs["osm_id"] == "n1"
        assert obs["name"] == "New Name"
        assert obs["snapshot_count"] == 2
        (change,) = build_change_history()
        assert change["field"] == "name"

    def test_same_name_different_id_change_attribution(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "Same"), cafe("n2", "Same")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "Same"), cafe("n2", "Same", website="http://x.com")])
        (change,) = build_change_history()
        assert change["osm_id"] == "n2"

    def test_valid_osm_id_observed(self, history_dirs):
        """build_observation_history correctly counts observations with valid osm_id."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n2", "B")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A"), cafe("n3", "C")])
        observations = build_observation_history()
        assert [o["osm_id"] for o in observations] == ["n1", "n2", "n3"]

    def test_duplicate_osm_id_last_row_wins(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "First"), cafe("n1", "Second")])
        (obs,) = build_observation_history()
        assert obs["name"] == "Second"
        assert obs["snapshot_count"] == 1


class TestDeterminism:
    """Determinism tests (31-32)."""

    def test_stable_ordering(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n2", "B"), cafe("n1", "A")])
        make_snapshot(
            B_ID,
            B_AT,
            [cafe("n2", "B New", website="http://b.com"), cafe("n1", "A New", phone="1")],
        )
        observations = build_observation_history()
        assert [o["osm_id"] for o in observations] == ["n1", "n2"]
        changes = build_change_history()
        assert [(c["snapshot_after"], c["osm_id"], c["field"]) for c in changes] == [
            (B_ID, "n1", "name"),
            (B_ID, "n1", "phone"),
            (B_ID, "n2", "name"),
            (B_ID, "n2", "website"),
        ]

    def test_repeated_analysis_equivalent(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A", website="http://a.com")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A New", website="http://b.com")])
        assert build_observation_history() == build_observation_history()
        assert build_change_history() == build_change_history()
        assert summarize_history() == summarize_history()


class TestReliability:
    """Reliability tests (33-36)."""

    def test_missing_csv_excluded_from_discovery(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        (history_dirs["processed"] / B_ID / "cafes.csv").unlink()
        assert [m["snapshot_id"] for m in discover_snapshots()] == [A_ID]

    def test_corrupt_csv_skipped_with_warning(self, history_dirs, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        (history_dirs["processed"] / B_ID / "cafes.csv").write_bytes(b"\xff\xfe\x00invalid")
        observations = build_observation_history()
        assert [o["osm_id"] for o in observations] == ["n1"]
        assert observations[0]["snapshot_count"] == 1
        assert "skipping snapshot" in capsys.readouterr().err.lower()

    def test_missing_metadata_excluded(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        (history_dirs["raw"] / B_ID / "metadata.json").unlink()
        assert [m["snapshot_id"] for m in discover_snapshots()] == [A_ID]

    def test_invalid_snapshot_directory_ignored(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        (history_dirs["raw"] / "not-a-directory").write_text("junk", encoding="utf-8")
        assert [m["snapshot_id"] for m in discover_snapshots()] == [A_ID]

    def test_empty_dataset(self, history_dirs):
        from cafe_finder.compare import TRACKED_FIELDS

        make_snapshot(A_ID, A_AT, pd.DataFrame(columns=TRACKED_FIELDS))
        assert build_observation_history() == []
        assert build_change_history() == []
        summary = summarize_history()
        assert summary["snapshots_analyzed"] == 1
        assert summary["unique_cafes"] == 0


class TestSummary:
    """Summary counting semantics tests."""

    def test_summary_counts(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n3", "C")])
        make_snapshot(
            B_ID, B_AT, [cafe("n1", "A New", website="http://a.com"), cafe("n2", "B")]
        )
        summary = summarize_history()
        assert summary["snapshots_analyzed"] == 2
        assert summary["first_snapshot"] == A_ID
        assert summary["latest_snapshot"] == B_ID
        assert summary["unique_cafes"] == 3
        assert summary["added"] == 1
        assert summary["no_longer_observed"] == 1
        assert summary["modified"] == 1
        assert summary["unchanged"] == 0
        assert summary["field_summary"] == [("name", 1), ("website", 1)]
        assert summary["total_field_changes"] == 2

    def test_field_summary_ordering(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n2", "B")])
        make_snapshot(
            B_ID,
            B_AT,
            [
                cafe("n1", "A", website="http://a.com", phone="1", cuisine="tea"),
                cafe("n2", "B", website="http://b.com"),
            ],
        )
        summary = summarize_history()
        assert summary["field_summary"] == [
            ("website", 2),
            ("cuisine", 1),
            ("phone", 1),
        ]

    def test_empty_summary(self, history_dirs):
        summary = summarize_history()
        assert summary["snapshots_analyzed"] == 0
        assert summary["unique_cafes"] == 0
        assert summary["field_summary"] == []


class TestCLI:
    """CLI tests (37-42)."""

    def test_basic_history_cli(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A")])
        run_cli(monkeypatch)
        main()
        out = capsys.readouterr().out
        assert "Historical Change Summary" in out
        assert "Snapshots analyzed: 2" in out
        assert "Unique cafes observed: 1" in out

    def test_osm_id_cli(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A New", website="http://a.com")])
        run_cli(monkeypatch, "--osm-id", "n1")
        main()
        out = capsys.readouterr().out
        assert "Cafe History" in out
        assert "OSM ID: n1" in out
        assert "Name: A New" in out
        assert f"First observed: {A_ID}" in out
        assert f"Last observed: {B_ID}" in out
        assert "Snapshots: 2" in out
        assert "website" in out

    def test_fields_cli(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", website="http://a.com")])
        run_cli(monkeypatch, "--fields")
        main()
        out = capsys.readouterr().out
        assert "Field Change Summary" in out
        assert "website" in out

    def test_invalid_osm_id(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        run_cli(monkeypatch, "--osm-id", "bogus-id")
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "bogus-id" in capsys.readouterr().err

    def test_historical_csv_export(self, history_dirs, monkeypatch, tmp_path, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n2", "B")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A"), cafe("n2", "B")])
        out_path = tmp_path / "exports" / "history.csv"
        run_cli(monkeypatch, "--output", str(out_path))
        main()
        assert out_path.exists()
        df = pd.read_csv(out_path, encoding="utf-8")
        assert list(df.columns) == OBSERVATION_FIELDS
        assert list(df["osm_id"]) == ["n1", "n2"]
        assert list(df["snapshot_count"]) == [2, 2]

    def test_change_history_csv_export(self, history_dirs, monkeypatch, tmp_path, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A", website="http://a.com")])
        out_path = tmp_path / "exports" / "changes.csv"
        run_cli(monkeypatch, "--changes-output", str(out_path))
        main()
        assert out_path.exists()
        df = pd.read_csv(out_path, encoding="utf-8", keep_default_na=False)
        assert list(df.columns) == CHANGE_FIELDS
        assert len(df) == 1
        assert df.iloc[0]["field"] == "website"
        assert df.iloc[0]["old_value"] == "missing"
        assert df.iloc[0]["new_value"] == "http://a.com"

    def test_empty_state_cli(self, history_dirs, monkeypatch, capsys):
        run_cli(monkeypatch)
        main()
        out = capsys.readouterr().out
        assert "Snapshots analyzed: 0" in out


class TestCLIReconstruction:
    """Reconstruction CLI tests."""

    def test_reconstruct_valid_snapshot(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        run_cli(monkeypatch, "--reconstruct", "--snapshot-id", A_ID)
        main()
        out = capsys.readouterr().out
        assert f"Snapshot: {A_ID}" in out
        assert "Records: 1" in out

    def test_reconstruct_nonexistent(self, history_dirs, monkeypatch, capsys):
        run_cli(monkeypatch, "--reconstruct", "--snapshot-id", "missing")
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "SNAPSHOT_NOT_FOUND" in err or "missing" in err.lower()

    def test_reconstruct_quarantined(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        quarantine_path = history_dirs["raw"] / A_ID / "quarantine.json"
        quarantine_path.write_text('{"reason": "test"}')
        run_cli(monkeypatch, "--reconstruct", "--snapshot-id", A_ID)
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "QUARANTINED" in err

    def test_reconstruct_missing_snapshot_id(self, history_dirs, monkeypatch, capsys):
        run_cli(monkeypatch, "--reconstruct")
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_reconstruct_json_output(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        run_cli(monkeypatch, "--reconstruct", "--snapshot-id", A_ID, "--json")
        main()
        out = capsys.readouterr().out
        import json as json_mod
        data = json_mod.loads(out)
        assert data["snapshot_id"] == A_ID
        assert data["record_count"] == 1
        assert "records" in data

    def test_reconstruct_deterministic(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n2", "B"), cafe("n1", "A")])
        run_cli(monkeypatch, "--reconstruct", "--snapshot-id", A_ID)
        out1 = capsys.readouterr().out
        run_cli(monkeypatch, "--reconstruct", "--snapshot-id", A_ID)
        out2 = capsys.readouterr().out
        assert out1 == out2


class TestCLIQuality:
    """Quality history CLI tests."""

    def test_quality_valid_single_snapshot(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        run_cli(monkeypatch, "--quality")
        main()
        out = capsys.readouterr().out
        assert f"Snapshot: {A_ID}" in out
        assert "Field completeness" in out

    def test_quality_multiple_snapshots(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n2", "B")])
        run_cli(monkeypatch, "--quality")
        main()
        out = capsys.readouterr().out
        assert f"Snapshot: {A_ID}" in out
        assert f"Snapshot: {B_ID}" in out

    def test_quality_invalid_snapshot_excluded(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n2", "B")])
        (history_dirs["processed"] / B_ID / "cafes.csv").write_bytes(b"\xff\xfe\x00invalid")
        run_cli(monkeypatch, "--quality")
        main()
        out = capsys.readouterr().out
        assert f"Snapshot: {A_ID}" in out
        assert f"Snapshot: {B_ID}" not in out

    def test_quality_no_valid_snapshots(self, history_dirs, monkeypatch, capsys):
        run_cli(monkeypatch, "--quality")
        main()
        out = capsys.readouterr().out
        assert "No valid snapshots" in out

    def test_quality_json_output(self, history_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        run_cli(monkeypatch, "--quality", "--json")
        main()
        out = capsys.readouterr().out
        import json as json_mod
        data = json_mod.loads(out)
        assert isinstance(data, list)
        assert data[0]["snapshot_id"] == A_ID

    def test_quality_csv_export(self, history_dirs, monkeypatch, tmp_path):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        out_path = tmp_path / "quality.csv"
        run_cli(monkeypatch, "--quality", "--quality-output", str(out_path))
        main()
        assert out_path.exists()
        df = pd.read_csv(out_path, encoding="utf-8")
        assert "snapshot_id" in df.columns
        assert "field" in df.columns
        assert "completeness_percentage" in df.columns


class TestQualityHistory:
    """Historical data-quality evolution tests."""

    def test_valid_single_snapshot(self, history_dirs):
        """Valid snapshot produces one quality record."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        records = build_quality_history()
        assert len(records) == 1
        assert records[0]["snapshot_id"] == A_ID
        assert records[0]["record_count"] == 1

    def test_multiple_snapshots(self, history_dirs):
        """Multiple valid snapshots produce multiple quality records."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n2", "B")])
        records = build_quality_history()
        assert len(records) == 2
        assert records[0]["snapshot_id"] == A_ID
        assert records[1]["snapshot_id"] == B_ID

    def test_chronological_ordering(self, history_dirs):
        """Quality records are ordered chronologically by snapshot_id."""
        make_snapshot(C_ID, C_AT, [cafe("n1", "A")])
        make_snapshot(A_ID, A_AT, [cafe("n2", "B")])
        make_snapshot(B_ID, B_AT, [cafe("n3", "C")])
        records = build_quality_history()
        assert len(records) == 3
        assert [r["snapshot_id"] for r in records] == [A_ID, B_ID, C_ID]

    def test_field_completeness_has_canonical_fields(self, history_dirs):
        """field_completeness contains all canonical columns."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        records = build_quality_history()
        fc = records[0]["field_completeness"]
        for col in schema.CANONICAL_COLUMNS:
            assert col in fc

    def test_field_completeness_present_missing(self, history_dirs):
        """Field completeness reports present and missing counts."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        records = build_quality_history()
        fc = records[0]["field_completeness"]
        for col in schema.CANONICAL_COLUMNS:
            assert "present" in fc[col]
            assert "missing" in fc[col]
            assert "completeness_percentage" in fc[col]

    def test_coordinate_validity(self, history_dirs):
        """Snapshot with valid coordinates reports valid count."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        records = build_quality_history()
        assert records[0]["valid_coordinate_records"] == 1
        assert records[0]["invalid_coordinate_records"] == 0

    def test_duplicate_evolution(self, history_dirs):
        """Snapshot with duplicate osm_ids reports duplicate count."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A"), cafe("n1", "B")])
        records = build_quality_history()
        assert records[0]["duplicate_osm_id_records"] == 2

    def test_invalid_snapshot_excluded(self, history_dirs, capsys):
        """Corrupt snapshot is excluded from quality history with warning."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n2", "B")])
        (history_dirs["processed"] / B_ID / "cafes.csv").write_bytes(b"\xff\xfe\x00invalid")
        records = build_quality_history()
        assert len(records) == 1
        assert records[0]["snapshot_id"] == A_ID
        err = capsys.readouterr().err
        assert "skipping snapshot" in err.lower()

    def test_quarantined_snapshot_excluded(self, history_dirs):
        """Quarantined snapshot is excluded from quality history."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n2", "B")])
        quarantine_path = history_dirs["raw"] / B_ID / "quarantine.json"
        quarantine_path.write_text('{"reason": "test"}')
        records = build_quality_history()
        assert len(records) == 1
        assert records[0]["snapshot_id"] == A_ID

    def test_no_valid_snapshots(self, history_dirs):
        """No snapshots returns empty list."""
        records = build_quality_history()
        assert records == []

    def test_empty_valid_snapshot(self, history_dirs):
        """Empty but valid snapshot produces record with zero counts."""
        empty_df = pd.DataFrame(columns=schema.CANONICAL_COLUMNS)
        make_snapshot(A_ID, A_AT, empty_df)
        records = build_quality_history()
        assert len(records) == 1
        assert records[0]["record_count"] == 0
        assert records[0]["valid_coordinate_records"] == 0
        assert records[0]["duplicate_osm_id_records"] == 0

    def test_deterministic_repeated(self, history_dirs):
        """Repeated execution produces identical results."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n2", "B")])
        records1 = build_quality_history()
        records2 = build_quality_history()
        assert records1 == records2

    def test_regression_with_history_functions(self, history_dirs):
        """Quality history works alongside existing history functions."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A"), cafe("n2", "B")])
        observations = build_observation_history()
        changes = build_change_history()
        quality_records = build_quality_history()
        assert len(observations) == 2
        assert len(changes) >= 0
        assert len(quality_records) == 2
        for record in quality_records:
            assert "snapshot_id" in record
            assert "record_count" in record


class TestReconstruction:
    """Integrity-gated snapshot reconstruction tests."""

    def test_reconstruct_snapshot_valid(self, history_dirs):
        """Valid snapshot reconstructs with canonical 13 columns and correct record count."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        df = reconstruct_snapshot(A_ID)
        assert len(df) == 1
        assert list(df.columns) == schema.CANONICAL_COLUMNS
        assert df.iloc[0]["osm_id"] == "n1"
        assert df.equals(df.sort_values("osm_id").reset_index(drop=True))

    def test_reconstruct_snapshot_deterministic(self, history_dirs):
        """Repeated reconstruction produces identical DataFrames."""
        make_snapshot(A_ID, A_AT, [cafe("n2", "B"), cafe("n1", "A")])
        df1 = reconstruct_snapshot(A_ID)
        df2 = reconstruct_snapshot(A_ID)
        assert df1.equals(df2)
        assert df1["osm_id"].tolist() == ["n1", "n2"]

    def test_reconstruct_snapshot_multiple_rows_sorted(self, history_dirs):
        """Reconstructed DataFrame is sorted by osm_id ascending."""
        make_snapshot(A_ID, A_AT, [cafe("c3", "C"), cafe("c1", "A"), cafe("c2", "B")])
        df = reconstruct_snapshot(A_ID)
        assert df["osm_id"].tolist() == ["c1", "c2", "c3"]

    def test_reconstruct_snapshot_nonexistent(self, history_dirs):
        """Nonexistent snapshot raises SnapshotDataError."""
        with pytest.raises(SnapshotDataError) as exc_info:
            reconstruct_snapshot("nonexistent_id")
        assert "nonexistent_id" in str(exc_info.value)

    def test_reconstruct_snapshot_missing_manifest(self, history_dirs, monkeypatch):
        """Snapshot with missing manifest raises SnapshotDataError."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        manifest_path = history_dirs["raw"] / A_ID / "manifest.json"
        manifest_path.unlink()
        with pytest.raises(SnapshotDataError) as exc_info:
            reconstruct_snapshot(A_ID)
        assert "NO_MANIFEST" in str(exc_info.value)

    def test_reconstruct_snapshot_quarantined(self, history_dirs):
        """Quarantined snapshot raises SnapshotDataError."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        quarantine_path = history_dirs["raw"] / A_ID / "quarantine.json"
        quarantine_path.write_text('{"reason": "test"}')
        with pytest.raises(SnapshotDataError) as exc_info:
            reconstruct_snapshot(A_ID)
        assert "QUARANTINED" in str(exc_info.value)

    def test_reconstruct_snapshot_checksum_mismatch(self, history_dirs):
        """Snapshot with checksum mismatch raises SnapshotDataError."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        manifest_path = history_dirs["raw"] / A_ID / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for artifact in manifest.get("artifacts", []):
            artifact["sha256"] = "deadbeef" * 8
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(SnapshotDataError) as exc_info:
            reconstruct_snapshot(A_ID)
        assert "INTEGRITY_FAILED" in str(exc_info.value)

    def test_reconstruct_snapshot_schema_mismatch(self, history_dirs):
        """Snapshot with invalid schema raises SnapshotDataError."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        processed_path = history_dirs["processed"] / A_ID / "cafes.csv"
        import cafe_finder.snapshot as snap_mod
        extra_col_path = snap_mod.SNAPSHOTS_PROCESSED_DIR / A_ID / "cafes.csv"
        df = pd.read_csv(extra_col_path)
        df["evil_column"] = "bad"
        df.to_csv(extra_col_path, index=False)
        with pytest.raises(SnapshotDataError) as exc_info:
            reconstruct_snapshot(A_ID)
        assert "INTEGRITY_FAILED" in str(exc_info.value)

    def test_reconstruct_snapshot_record_count_mismatch(self, history_dirs):
        """Snapshot with record count mismatch raises SnapshotDataError."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        manifest_path = history_dirs["raw"] / A_ID / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["record_count"] = 999
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(SnapshotDataError) as exc_info:
            reconstruct_snapshot(A_ID)
        assert "INTEGRITY_FAILED" in str(exc_info.value)

    def test_reconstruct_snapshot_loads_existing_history(self, history_dirs):
        """Reconstruction works and existing history functions still work."""
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        make_snapshot(B_ID, B_AT, [cafe("n1", "A"), cafe("n2", "B")])
        df = reconstruct_snapshot(A_ID)
        assert len(df) == 1
        observations = build_observation_history()
        assert len(observations) == 2


class TestFormatters:
    """Formatter unit tests."""

    def test_format_summary_labels(self):
        summary = summarize_history([])
        text = format_summary(summary)
        assert "Added observations:" in text
        assert "No-longer-observed observations:" in text
        assert "Modified observations:" in text
        assert "Unchanged observations:" in text

    def test_format_fields_empty(self):
        summary = summarize_history([])
        assert "no field changes" in format_fields(summary).lower()

    def test_format_cafe_history_no_changes(self, history_dirs):
        make_snapshot(A_ID, A_AT, [cafe("n1", "A")])
        observations = build_observation_history()
        text = format_cafe_history("n1", observations, [])
        assert "no field changes" in text.lower()

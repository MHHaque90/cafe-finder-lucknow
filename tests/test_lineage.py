"""Tests for historical-analysis lineage (Phase 9)."""

import json
import sys
from datetime import datetime, timezone

import pandas as pd
import pytest

from cafe_finder import integrity, schema
from cafe_finder.lineage import (
    ANALYSIS_TYPE,
    LineageError,
    export_lineage_json,
    format_lineage,
    generate_lineage,
    main,
)

A_ID = "2026-08-01T120000Z"
A_AT = "2026-08-01T12:00:00+00:00"
B_ID = "2026-08-15T120000Z"
B_AT = "2026-08-15T12:00:00+00:00"


@pytest.fixture
def lineage_dirs(tmp_path, monkeypatch):
    """Redirect Phase 8 snapshot dirs to temp locations."""
    import cafe_finder.snapshot as snap_mod

    raw = tmp_path / "raw" / "snapshots"
    processed = tmp_path / "processed" / "snapshots"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    monkeypatch.setattr(snap_mod, "SNAPSHOTS_RAW_DIR", raw)
    monkeypatch.setattr(snap_mod, "SNAPSHOTS_PROCESSED_DIR", processed)
    return {"raw": raw, "processed": processed}


def make_snapshot(snapshot_id, retrieved_at, rows):
    """Create a complete synthetic snapshot (raw + processed + metadata + manifest)."""
    import cafe_finder.snapshot as snap_mod
    from cafe_finder.snapshot import save_processed_snapshot, save_raw_snapshot
    from cafe_finder import integrity, schema

    df = pd.DataFrame(rows)
    save_raw_snapshot(
        records=[dict(r) for r in rows],
        snapshot_id=snapshot_id,
        retrieved_at_utc=retrieved_at,
        query="test-query",
    )
    save_processed_snapshot(
        df=df, snapshot_id=snapshot_id, retrieved_at_utc=retrieved_at, query="test-query"
    )
    # Create minimal manifest for Phase 10 compatibility
    snapshot_dir = snap_mod.SNAPSHOTS_RAW_DIR / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    processed_snapshot_dir = snap_mod.SNAPSHOTS_PROCESSED_DIR / snapshot_id
    processed_snapshot_dir.mkdir(parents=True, exist_ok=True)
    raw_file = snapshot_dir / "raw.json"
    processed_file = snap_mod.SNAPSHOTS_PROCESSED_DIR / snapshot_id / "cafes.csv"
    artifacts = [
        {"path": f"data/raw/snapshots/{snapshot_id}/raw.json", "sha256": integrity.sha256_file(raw_file), "size_bytes": raw_file.stat().st_size},
        {"path": f"data/processed/snapshots/{snapshot_id}/cafes.csv", "sha256": integrity.sha256_file(processed_file), "size_bytes": processed_file.stat().st_size},
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
        "record_count": len(rows),
        "artifacts": artifacts,
        "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
    }
    final = {**draft, "status": "success", "completed_at_utc": retrieved_at}
    (snapshot_dir / "manifest.json").write_text(json.dumps(final))


def base_rows():
    return [
        {"osm_id": "n1", "name": "A", "latitude": 26.85, "longitude": 80.94},
        {"osm_id": "n2", "name": "B", "latitude": 26.86, "longitude": 80.95},
    ]


class TestLineageContent:
    """Lineage content tests (1-10, 13)."""

    def test_single_snapshot_lineage(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        report = generate_lineage()
        assert report["snapshots_analyzed"] == 1
        assert report["snapshot_ids"] == [A_ID]
        assert report["first_snapshot"]["snapshot_id"] == A_ID
        assert report["latest_snapshot"]["snapshot_id"] == A_ID

    def test_multiple_snapshot_lineage(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        make_snapshot(B_ID, B_AT, base_rows())
        report = generate_lineage()
        assert report["snapshots_analyzed"] == 2
        assert report["first_snapshot"]["snapshot_id"] == A_ID
        assert report["latest_snapshot"]["snapshot_id"] == B_ID

    def test_correct_source(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        assert generate_lineage()["source"] == "OpenStreetMap"

    def test_correct_retrieval_method(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        assert generate_lineage()["retrieval_method"] == "Overpass API"

    def test_correct_snapshot_ids(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        make_snapshot(B_ID, B_AT, base_rows())
        assert generate_lineage()["snapshot_ids"] == [A_ID, B_ID]

    def test_correct_retrieval_timestamps(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        make_snapshot(B_ID, B_AT, base_rows())
        report = generate_lineage()
        assert report["first_snapshot"]["retrieved_at_utc"] == A_AT
        assert report["latest_snapshot"]["retrieved_at_utc"] == B_AT
        by_id = {s["snapshot_id"]: s for s in report["snapshots"]}
        assert by_id[A_ID]["retrieved_at_utc"] == A_AT
        assert by_id[B_ID]["retrieved_at_utc"] == B_AT

    def test_correct_record_counts(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        make_snapshot(B_ID, B_AT, base_rows() + [{"osm_id": "n3", "name": "C"}])
        report = generate_lineage()
        assert report["first_snapshot"]["record_count"] == 2
        assert report["latest_snapshot"]["record_count"] == 3

    def test_correct_artifact_references(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        report = generate_lineage()
        first = report["first_snapshot"]
        assert first["raw_file"] == "raw.json"
        assert first["processed_file"] == "cafes.csv"

    def test_correct_analysis_type(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        report = generate_lineage()
        assert report["analysis_type"] == ANALYSIS_TYPE
        assert report["analysis_type"] == "historical_change_analysis"

    def test_generation_timestamp_is_report_time(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        before = datetime.now(timezone.utc)
        report = generate_lineage()
        after = datetime.now(timezone.utc)
        generated = datetime.fromisoformat(report["generated_at_utc"])
        assert before <= generated <= after
        assert report["generated_at_utc"] != A_AT

    def test_deterministic_snapshot_ordering(self, lineage_dirs):
        make_snapshot(B_ID, B_AT, base_rows())
        make_snapshot(A_ID, A_AT, base_rows())
        report = generate_lineage()
        assert report["snapshot_ids"] == [A_ID, B_ID]
        assert [s["snapshot_id"] for s in report["snapshots"]] == [A_ID, B_ID]

    def test_repeated_lineage_equivalent_except_timestamp(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        first = generate_lineage()
        second = generate_lineage()
        first.pop("generated_at_utc")
        second.pop("generated_at_utc")
        assert first == second


class TestLineageErrors:
    """Lineage error handling tests (11-12)."""

    def test_missing_metadata_no_snapshots(self, lineage_dirs):
        with pytest.raises(LineageError):
            generate_lineage()

    def test_invalid_metadata_rejected(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        from cafe_finder.snapshot import load_snapshot_metadata

        assert load_snapshot_metadata(A_ID) is not None
        (lineage_dirs["raw"] / A_ID / "metadata.json").write_text(
            json.dumps({"snapshot_id": A_ID}), encoding="utf-8"
        )
        with pytest.raises(LineageError):
            generate_lineage()

    def test_incomplete_snapshot_excluded(self, lineage_dirs):
        from cafe_finder.snapshot import save_raw_snapshot

        make_snapshot(A_ID, A_AT, base_rows())
        save_raw_snapshot(
            records=[{"osm_id": "n9"}],
            snapshot_id=B_ID,
            retrieved_at_utc=B_AT,
            query="test-query",
        )
        report = generate_lineage()
        assert report["snapshot_ids"] == [A_ID]


class TestLineageExport:
    """Lineage export test (14)."""

    def test_json_export(self, lineage_dirs, tmp_path):
        make_snapshot(A_ID, A_AT, base_rows())
        make_snapshot(B_ID, B_AT, base_rows())
        report = generate_lineage()
        out_path = tmp_path / "exports" / "lineage.json"
        export_lineage_json(report, out_path)
        assert out_path.exists()
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert loaded["analysis_type"] == "historical_change_analysis"
        assert loaded["snapshot_ids"] == [A_ID, B_ID]
        assert loaded["first_snapshot"]["retrieved_at_utc"] == A_AT
        assert loaded["latest_snapshot"]["retrieved_at_utc"] == B_AT
        assert loaded["generated_at_utc"]


class TestLineageCLI:
    """Lineage CLI tests (15)."""

    def test_cli_output(self, lineage_dirs, monkeypatch, capsys):
        make_snapshot(A_ID, A_AT, base_rows())
        make_snapshot(B_ID, B_AT, base_rows())
        monkeypatch.setattr(sys, "argv", ["lineage"])
        main()
        out = capsys.readouterr().out
        assert "Historical Analysis Lineage" in out
        assert "Source: OpenStreetMap" in out
        assert "Retrieval method: Overpass API" in out
        assert "Snapshots analyzed: 2" in out
        assert A_ID in out
        assert B_ID in out
        assert A_AT in out

    def test_cli_json_export(self, lineage_dirs, monkeypatch, tmp_path, capsys):
        make_snapshot(A_ID, A_AT, base_rows())
        out_path = tmp_path / "exports" / "lineage.json"
        monkeypatch.setattr(sys, "argv", ["lineage", "--output", str(out_path)])
        main()
        assert out_path.exists()
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert loaded["snapshot_ids"] == [A_ID]

    def test_cli_no_snapshots_fails(self, lineage_dirs, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["lineage"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "no valid successful snapshots" in capsys.readouterr().err.lower()

    def test_format_lineage_labels(self, lineage_dirs):
        make_snapshot(A_ID, A_AT, base_rows())
        text = format_lineage(generate_lineage())
        assert "First snapshot:" in text
        assert "Latest snapshot:" in text
        assert "Analysis generated:" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
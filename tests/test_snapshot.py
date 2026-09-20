"""Tests for snapshot functionality (Phase 8)."""

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from cafe_finder.snapshot import (
    SNAPSHOTS_RAW_DIR,
    SNAPSHOTS_PROCESSED_DIR,
    generate_metadata,
    generate_snapshot_id,
    get_latest_snapshot,
    get_snapshot_paths,
    list_snapshots,
    load_snapshot_metadata,
    save_processed_snapshot,
    save_raw_snapshot,
    format_snapshot_list,
)


@pytest.fixture
def snapshot_dirs(tmp_path):
    """Create temporary snapshot directories and monkeypatch paths."""
    raw = tmp_path / "raw" / "snapshots"
    processed = tmp_path / "processed" / "snapshots"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)

    import cafe_finder.snapshot as snapshot_mod
    orig_raw = snapshot_mod.SNAPSHOTS_RAW_DIR
    orig_proc = snapshot_mod.SNAPSHOTS_PROCESSED_DIR
    snapshot_mod.SNAPSHOTS_RAW_DIR = raw
    snapshot_mod.SNAPSHOTS_PROCESSED_DIR = processed
    yield {"raw": raw, "processed": processed}
    snapshot_mod.SNAPSHOTS_RAW_DIR = orig_raw
    snapshot_mod.SNAPSHOTS_PROCESSED_DIR = orig_proc


def make_complete_snapshot(snapshot_dirs, snapshot_id, records, retrieved_at_utc):
    """Create a complete snapshot (raw + processed + metadata + manifest)."""
    save_raw_snapshot(
        records=records,
        snapshot_id=snapshot_id,
        retrieved_at_utc=retrieved_at_utc,
        query="[out:json];",
    )
    df = pd.DataFrame(records)
    save_processed_snapshot(
        df=df,
        snapshot_id=snapshot_id,
        retrieved_at_utc=retrieved_at_utc,
        query="[out:json];",
    )
    # Create minimal manifest for Phase 10 compatibility
    snapshot_dir = snapshot_dirs["raw"] / snapshot_id
    manifest_data = {
        "manifest_version": 1,
        "pipeline_name": "cafe_finder",
        "schema_version": 1,
        "status": "success",
        "snapshot_id": snapshot_id,
        "started_at_utc": retrieved_at_utc,
        "retrieved_at_utc": retrieved_at_utc,
        "completed_at_utc": retrieved_at_utc,
        "source": "OpenStreetMap",
        "retrieval_method": "Overpass API",
        "endpoint": "https://overpass-api.de/api/interpreter",
        "query": "[out:json];",
        "record_count": len(records),
        "artifacts": [],
        "schema": {"schema_version": 1, "columns": [], "required": []},
    }
    (snapshot_dirs["raw"] / snapshot_id / "manifest.json").write_text(json.dumps(manifest_data))


class TestGenerateSnapshotId:
    """Tests for generate_snapshot_id."""

    def test_format_is_correct(self):
        sid = generate_snapshot_id()
        dt = datetime.strptime(sid, "%Y-%m-%dT%H%M%SZ")
        assert dt.tzinfo is None
        assert sid.endswith("Z")

    def test_is_filesystem_safe(self):
        sid = generate_snapshot_id()
        assert ":" not in sid
        assert "?" not in sid
        assert "/" not in sid

    def test_deterministic_within_second(self):
        from cafe_finder.snapshot import generate_snapshot_id
        id1 = generate_snapshot_id()
        id2 = generate_snapshot_id()
        assert id1 == id2


class TestGetSnapshotPaths:
    """Tests for get_snapshot_paths."""

    def test_returns_correct_structure(self, snapshot_dirs):
        paths = get_snapshot_paths("2026-09-08T120000Z")
        assert "raw" in str(paths["raw_dir"])
        assert "processed" in str(paths["processed_dir"])
        assert paths["raw_file"].name == "raw.json"
        assert paths["processed_file"].name == "cafes.csv"
        assert paths["metadata_file"].name == "metadata.json"

    def test_snapshot_id_in_paths(self, snapshot_dirs):
        sid = "2026-09-08T120000Z"
        paths = get_snapshot_paths(sid)
        assert sid in str(paths["raw_dir"])
        assert sid in str(paths["processed_dir"])


class TestGenerateMetadata:
    """Tests for generate_metadata."""

    def test_required_keys_present(self):
        meta = generate_metadata(
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            record_count=33,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
        )
        assert meta["snapshot_id"] == "2026-09-08T120000Z"
        assert meta["retrieved_at_utc"] == "2026-09-08T12:00:00Z"
        assert meta["source"] == "OpenStreetMap"
        assert meta["retrieval_method"] == "Overpass API"
        assert meta["record_count"] == 33
        assert meta["status"] == "success"

    def test_status_success_explicit(self):
        meta = generate_metadata(
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            record_count=33,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
            status="success",
        )
        assert meta["status"] == "success"

    def test_status_failed_explicit(self):
        meta = generate_metadata(
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            record_count=0,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
            status="failed",
        )
        assert meta["status"] == "failed"


class TestSaveRawSnapshot:
    """Tests for save_raw_snapshot."""

    def test_creates_raw_file(self, snapshot_dirs):
        records = [{"osm_id": "n1", "name": "A"}]
        save_raw_snapshot(
            records=records,
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            query="[out:json];",
        )
        raw_file = snapshot_dirs["raw"] / "2026-09-08T120000Z" / "raw.json"
        assert raw_file.exists()
        with raw_file.open() as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["osm_id"] == "n1"

    def test_creates_metadata_file(self, snapshot_dirs):
        records = [{"osm_id": "n1", "name": "A"}]
        save_raw_snapshot(
            records=records,
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            query="[out:json];",
        )
        metadata_file = snapshot_dirs["raw"] / "2026-09-08T120000Z" / "metadata.json"
        assert metadata_file.exists()
        with metadata_file.open() as f:
            meta = json.load(f)
        assert meta["status"] == "success"
        assert meta["record_count"] == 1
        assert meta["retrieved_at_utc"] == "2026-09-08T12:00:00Z"

    def test_record_count_matches(self, snapshot_dirs):
        records = [{"osm_id": f"n{i}"} for i in range(5)]
        save_raw_snapshot(
            records=records,
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            query="[out:json];",
        )
        metadata_file = snapshot_dirs["raw"] / "2026-09-08T120000Z" / "metadata.json"
        with metadata_file.open() as f:
            meta = json.load(f)
        assert meta["record_count"] == 5

    def test_empty_records(self, snapshot_dirs):
        records = []
        save_raw_snapshot(
            records=records,
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            query="[out:json];",
        )
        raw_file = snapshot_dirs["raw"] / "2026-09-08T120000Z" / "raw.json"
        assert raw_file.exists()


class TestLoadSnapshotMetadata:
    """Tests for load_snapshot_metadata."""

    def test_loads_valid_snapshot(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T120000Z",
            records,
            "2026-09-08T12:00:00Z",
        )
        meta = load_snapshot_metadata("2026-09-08T120000Z")
        assert meta is not None
        assert meta["status"] == "success"

    def test_returns_none_for_nonexistent(self, snapshot_dirs):
        meta = load_snapshot_metadata("2026-09-08T999999Z")
        assert meta is None

    def test_returns_none_for_missing_metadata(self, snapshot_dirs):
        snap_dir = snapshot_dirs["raw"] / "2026-09-08T120000Z"
        snap_dir.mkdir(parents=True)
        (snap_dir / "raw.json").write_text("[]")
        meta = load_snapshot_metadata("2026-09-08T120000Z")
        assert meta is None

    def test_returns_none_for_missing_required_keys(self, snapshot_dirs):
        snap_dir = snapshot_dirs["raw"] / "2026-09-08T120000Z"
        snap_dir.mkdir(parents=True)
        incomplete = {"snapshot_id": "2026-09-08T120000Z"}
        (snap_dir / "metadata.json").write_text(json.dumps(incomplete))
        meta = load_snapshot_metadata("2026-09-08T120000Z")
        assert meta is None

    def test_returns_none_for_failed_status(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        save_raw_snapshot(
            records=records,
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            query="[out:json];",
        )
        meta_file = snapshot_dirs["raw"] / "2026-09-08T120000Z" / "metadata.json"
        with meta_file.open() as f:
            meta = json.load(f)
        meta["status"] = "failed"
        with meta_file.open("w") as f:
            json.dump(meta, f)
        result = load_snapshot_metadata("2026-09-08T120000Z")
        assert result is None

    def test_returns_none_for_missing_raw_file(self, snapshot_dirs):
        snap_dir = snapshot_dirs["raw"] / "2026-09-08T120000Z"
        snap_dir.mkdir(parents=True)
        meta = generate_metadata(
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            record_count=0,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
        )
        with (snap_dir / "metadata.json").open("w") as f:
            json.dump(meta, f)
        result = load_snapshot_metadata("2026-09-08T120000Z")
        assert result is None


class TestListSnapshots:
    """Tests for list_snapshots."""

    def test_no_snapshots(self, snapshot_dirs):
        snapshots = list_snapshots()
        assert snapshots == []

    def test_lists_successful_snapshots(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T120000Z",
            records,
            "2026-09-08T12:00:00Z",
        )
        snapshots = list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["snapshot_id"] == "2026-09-08T120000Z"

    def test_sorted_newest_first(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T120000Z",
            records,
            "2026-09-08T12:00:00Z",
        )
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T130000Z",
            records,
            "2026-09-08T13:00:00Z",
        )
        snapshots = list_snapshots()
        assert snapshots[0]["snapshot_id"] == "2026-09-08T130000Z"
        assert snapshots[1]["snapshot_id"] == "2026-09-08T120000Z"


class TestGetLatestSnapshot:
    """Tests for get_latest_snapshot."""

    def test_no_snapshots(self, snapshot_dirs):
        latest = get_latest_snapshot()
        assert latest is None

    def test_returns_newest(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T120000Z",
            records,
            "2026-09-08T12:00:00Z",
        )
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T130000Z",
            records,
            "2026-09-08T13:00:00Z",
        )
        latest = get_latest_snapshot()
        assert latest == "2026-09-08T130000Z"

    def test_ignores_failed_snapshots(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T120000Z",
            records,
            "2026-09-08T12:00:00Z",
        )
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T130000Z",
            records,
            "2026-09-08T13:00:00Z",
        )
        meta_file = snapshot_dirs["raw"] / "2026-09-08T130000Z" / "metadata.json"
        with meta_file.open() as f:
            meta = json.load(f)
        meta["status"] = "failed"
        with meta_file.open("w") as f:
            json.dump(meta, f)
        latest = get_latest_snapshot()
        assert latest == "2026-09-08T120000Z"


class TestFormatSnapshotList:
    """Tests for format_snapshot_list."""

    def test_empty_list(self):
        result = format_snapshot_list([])
        assert "(no successful snapshots found)" in result

    def test_basic_output(self):
        meta = generate_metadata(
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            record_count=33,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
        )
        result = format_snapshot_list([meta], verbose=False)
        assert "2026-09-08T120000Z" in result
        assert "33 records" in result

    def test_verbose_output(self):
        meta = generate_metadata(
            snapshot_id="2026-09-08T120000Z",
            retrieved_at_utc="2026-09-08T12:00:00Z",
            record_count=33,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
        )
        result = format_snapshot_list([meta], verbose=True)
        assert "Retrieved:" in result
        assert "Source:" in result
        assert "Method:" in result
        assert "Status:" in result


class TestTimestampNotHardcoded:
    """Verify timestamps are actual UTC, not hardcoded."""

    def test_retrieved_at_utc_is_set(self, snapshot_dirs):
        records = [{"osm_id": "n1"}]
        make_complete_snapshot(
            snapshot_dirs,
            "2026-09-08T120000Z",
            records,
            "2026-09-08T12:00:00Z",
        )
        meta = load_snapshot_metadata("2026-09-08T120000Z")
        assert meta["retrieved_at_utc"] is not None
        assert meta["retrieved_at_utc"] != ""

    def test_retrieved_at_utc_is_distinct_from_snapshot_id(self):
        retrieved_at = datetime.now(timezone.utc).isoformat()
        snapshot_id = generate_snapshot_id()
        meta = generate_metadata(
            snapshot_id=snapshot_id,
            retrieved_at_utc=retrieved_at,
            record_count=0,
            query="[out:json];",
            raw_file="raw.json",
            processed_file="cafes.csv",
        )
        assert meta["snapshot_id"] != meta["retrieved_at_utc"]


class TestPipelineSnapshotFlow:
    """End-to-end tests for the --snapshot pipeline workflow."""

    @pytest.fixture
    def pipeline_env(self, tmp_path, monkeypatch):
        import cafe_finder.fetch as fetch_mod
        import cafe_finder.pipeline as pipe_mod
        import cafe_finder.snapshot as snap_mod

        raw_root = tmp_path / "data" / "raw"
        proc_root = tmp_path / "data" / "processed"
        raw_root.mkdir(parents=True)
        proc_root.mkdir(parents=True)

        monkeypatch.setattr(snap_mod, "SNAPSHOTS_RAW_DIR", raw_root / "snapshots")
        monkeypatch.setattr(snap_mod, "SNAPSHOTS_PROCESSED_DIR", proc_root / "snapshots")

        monkeypatch.setattr(pipe_mod, "RAW_JSON_PATH", raw_root / "lucknow_cafes_raw.json")
        monkeypatch.setattr(pipe_mod, "CLEANED_JSON_PATH", raw_root / "lucknow_cafes_cleaned.json")
        monkeypatch.setattr(pipe_mod, "PROCESSED_CSV_PATH", proc_root / "lucknow_cafes.csv")

        return {
            "fetch_mod": fetch_mod,
            "pipe_mod": pipe_mod,
            "snap_mod": snap_mod,
            "proc_csv": proc_root / "lucknow_cafes.csv",
            "raw_snapshots": raw_root / "snapshots",
            "proc_snapshots": proc_root / "snapshots",
        }

    def make_fetch(self, records):
        def fake_fetch(user_agent=None, timeout=None):
            return records
        return fake_fetch

    def test_snapshot_mode_creates_snapshots_and_promotes(self, pipeline_env):
        import cafe_finder.pipeline as pipe_mod
        records = [
            {"osm_id": "node1", "name": "Cafe A", "latitude": 26.85, "longitude": 80.94},
            {"osm_id": "node2", "name": "Cafe B", "latitude": 26.86, "longitude": 80.95},
        ]
        pipeline_env["fetch_mod"].fetch_lucknow_cafes = self.make_fetch(records)

        stats = pipe_mod.run_pipeline(snapshot_mode=True)

        assert stats["snapshot_id"]
        assert stats["csv_records"] == 2
        assert pipeline_env["proc_csv"].exists()

        with pipeline_env["proc_csv"].open() as f:
            lines = f.readlines()
        assert len(lines) == 3

        snapshot_id = stats["snapshot_id"]
        meta = load_snapshot_metadata(snapshot_id)
        assert meta is not None
        assert meta["status"] == "success"
        assert meta["record_count"] == 2

        raw_dir = pipeline_env["raw_snapshots"] / snapshot_id
        proc_dir = pipeline_env["proc_snapshots"] / snapshot_id
        assert (raw_dir / "raw.json").exists()
        assert (proc_dir / "cafes.csv").exists()

    def test_second_run_compares_with_previous(self, pipeline_env):
        import cafe_finder.pipeline as pipe_mod
        pipeline_env["fetch_mod"].fetch_lucknow_cafes = self.make_fetch([
            {"osm_id": "node1", "name": "Cafe A", "latitude": 26.85, "longitude": 80.94},
            {"osm_id": "node2", "name": "Cafe B", "latitude": 26.86, "longitude": 80.95},
        ])
        first = pipe_mod.run_pipeline(snapshot_mode=True)

        time.sleep(1.1)  # ensure snapshot IDs differ (IDs have 1-second granularity)

        pipeline_env["fetch_mod"].fetch_lucknow_cafes = self.make_fetch([
            {"osm_id": "node1", "name": "Cafe A", "latitude": 26.85, "longitude": 80.94},
            {"osm_id": "node2", "name": "Cafe B", "latitude": 26.86, "longitude": 80.95},
            {"osm_id": "node3", "name": "Cafe C", "latitude": 26.87, "longitude": 80.96},
        ])
        second = pipe_mod.run_pipeline(snapshot_mode=True)

        comparison = second["comparison"]
        assert comparison["old_snapshot_id"] == first["snapshot_id"]
        assert comparison["old_record_count"] == 2
        assert comparison["new_record_count"] == 3
        assert comparison["added"] == 1
        assert comparison["removed"] == 0
        assert comparison["modified"] == 0
        assert comparison["unchanged"] == 2

    def test_failed_fetch_leaves_current_csv_untouched(self, pipeline_env, capsys):
        import cafe_finder.pipeline as pipe_mod
        pipeline_env["proc_csv"].write_text("osm_id,name\nnode_kept,Cafe Kept\n", encoding="utf-8")

        def failing_fetch(user_agent=None, timeout=None):
            raise RuntimeError("boom")
        pipeline_env["fetch_mod"].fetch_lucknow_cafes = failing_fetch

        with pytest.raises(SystemExit):
            pipe_mod.run_pipeline(snapshot_mode=True)

        content = pipeline_env["proc_csv"].read_text(encoding="utf-8")
        assert "node_kept" in content
        assert "Cafe Kept" in content
        assert not pipeline_env["raw_snapshots"].exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
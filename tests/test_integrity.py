"""Tests for integrity verification (Phase 10)."""

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from cafe_finder import integrity, manifest, schema, snapshot


def make_valid_df() -> pd.DataFrame:
    """Create a valid DataFrame with all 13 canonical columns."""
    return pd.DataFrame([{
        "osm_id": "node12345",
        "name": "Test Cafe",
        "latitude": 26.85,
        "longitude": 80.95,
        "street": "Test Street",
        "housenumber": "123",
        "city": "Lucknow",
        "postcode": "226001",
        "cuisine": "cafe",
        "opening_hours": "08:00-22:00",
        "website": "http://example.com",
        "phone": "+91-1234567890",
        "source": "OpenStreetMap",
    }])


@pytest.fixture
def snapshot_dirs(tmp_path: Path) -> dict:
    """Create temporary snapshot directories and monkeypatch paths."""
    raw = tmp_path / "raw" / "snapshots"
    processed = tmp_path / "processed" / "snapshots"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)

    import cafe_finder.snapshot as snapshot_mod
    import cafe_finder.integrity as integrity_mod
    import cafe_finder.manifest as manifest_mod

    orig_raw = snapshot_mod.SNAPSHOTS_RAW_DIR
    orig_proc = snapshot_mod.SNAPSHOTS_PROCESSED_DIR
    orig_proc_csv = integrity_mod.PROCESSED_CSV_PATH

    snapshot_mod.SNAPSHOTS_RAW_DIR = raw
    snapshot_mod.SNAPSHOTS_PROCESSED_DIR = processed
    integrity_mod.PROCESSED_CSV_PATH = tmp_path / "processed" / "lucknow_cafes.csv"

    yield {"raw": raw, "processed": processed, "tmp": tmp_path}

    snapshot_mod.SNAPSHOTS_RAW_DIR = orig_raw
    snapshot_mod.SNAPSHOTS_PROCESSED_DIR = orig_proc
    integrity_mod.PROCESSED_CSV_PATH = orig_proc_csv


def create_complete_snapshot(snapshot_dirs: dict, snapshot_id: str, df: pd.DataFrame) -> dict:
    """Create a complete snapshot with valid manifest."""
    raw_dir = snapshot_dirs["raw"]
    processed_dir = snapshot_dirs["processed"]

    snapshot_dir = raw_dir / snapshot_id
    snapshot_dir.mkdir(parents=True)
    processed_snapshot_dir = processed_dir / snapshot_id
    processed_snapshot_dir.mkdir(parents=True)

    # Raw file
    raw_file = snapshot_dir / "raw.json"
    raw_file.write_text("[]")

    # Processed file
    processed_file = processed_snapshot_dir / "cafes.csv"
    df.to_csv(processed_file, index=False)

    # Compute actual checksums
    raw_sha = integrity.sha256_file(raw_file)
    processed_sha = integrity.sha256_file(processed_file)

    # Metadata
    metadata = {
        "snapshot_id": snapshot_id,
        "retrieved_at_utc": "2026-09-13T06:32:40Z",
        "source": "OpenStreetMap",
        "retrieval_method": "Overpass API",
        "endpoint": "https://overpass-api.de/api/interpreter",
        "query": "[out:json];nwr;out;",
        "record_count": len(df),
        "raw_file": "raw.json",
        "processed_file": "cafes.csv",
        "status": "success",
    }
    (snapshot_dir / "metadata.json").write_text(json.dumps(metadata))

    # Manifest - use absolute paths for artifacts
    artifacts = [
        {"path": str(raw_file), "sha256": integrity.sha256_file(raw_file), "size_bytes": raw_file.stat().st_size},
        {"path": str(processed_file), "sha256": integrity.sha256_file(processed_file), "size_bytes": processed_file.stat().st_size},
    ]
    draft = {
        "manifest_version": 1,
        "pipeline_name": "cafe_finder",
        "schema_version": 1,
        "status": "preparing",
        "snapshot_id": snapshot_id,
        "started_at_utc": "2026-09-13T06:32:35Z",
        "retrieved_at_utc": "2026-09-13T06:32:40Z",
        "source": "OpenStreetMap",
        "retrieval_method": "Overpass API",
        "endpoint": "https://overpass-api.de/api/interpreter",
        "query": "[out:json];nwr;out;",
        "record_count": len(df),
        "artifacts": artifacts,
        "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
    }
    final = {
        **draft,
        "status": "success",
        "completed_at_utc": "2026-09-13T06:32:41Z",
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(final))

    return {"snapshot_id": snapshot_id, "df": df, "raw_sha": raw_sha, "processed_sha": processed_sha}


class TestSha256:
    """Tests for SHA-256 checksums."""

    def test_known_vector_abc(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"abc")
            path = Path(f.name)
        try:
            sha = integrity.sha256_file(path)
            assert sha == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        finally:
            path.unlink()

    def test_known_vector_empty(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            path = Path(f.name)
        try:
            sha = integrity.sha256_file(path)
            assert sha == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        finally:
            path.unlink()

    def test_repeated_checksum_same(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test data")
            path = Path(f.name)
        try:
            sha1 = integrity.sha256_file(path)
            sha2 = integrity.sha256_file(path)
            assert sha1 == sha2
        finally:
            path.unlink()

    def test_changed_content_different_hash(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test")
            path = Path(f.name)
        try:
            sha1 = integrity.sha256_file(path)
            with path.open("wb") as f:
                f.write(b"test2")
            sha2 = integrity.sha256_file(path)
            assert sha1 != sha2
        finally:
            path.unlink()

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            integrity.sha256_file(Path("/nonexistent/file"))


class TestArtifactVerification:
    """Tests for verify_artifact()."""

    def test_valid_artifact(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test data")
            path = Path(f.name)
        try:
            sha = integrity.sha256_file(path)
            size = path.stat().st_size
            result = integrity.verify_artifact(path, sha, size)
            assert result["valid"] is True
            assert result["sha_match"] is True
            assert result["size_match"] is True
        finally:
            path.unlink()

    def test_modified_artifact(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"original")
            path = Path(f.name)
        try:
            sha = integrity.sha256_file(path)
            size = path.stat().st_size
            with path.open("wb") as f:
                f.write(b"modified")
            result = integrity.verify_artifact(path, sha, size)
            assert result["valid"] is False
            assert result["sha_match"] is False
        finally:
            path.unlink()

    def test_missing_artifact(self):
        result = integrity.verify_artifact(Path("/nonexistent"), "sha", 100)
        assert result["valid"] is False
        assert result["exists"] is False

    def test_size_mismatch(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test")
            path = Path(f.name)
        try:
            sha = integrity.sha256_file(path)
            result = integrity.verify_artifact(path, sha, 999)
            assert result["valid"] is False
            assert result["size_match"] is False
        finally:
            path.unlink()


class TestIntegrityVerification:
    """Tests for verify_snapshot() and verify_latest()."""

    def test_complete_snapshot_passes(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "PASSED"

    def test_missing_raw_artifact_incomplete(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        raw_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "raw.json"
        raw_file.unlink()
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INCOMPLETE"

    def test_missing_processed_artifact_incomplete(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        processed_file = snapshot_dirs["processed"] / snap["snapshot_id"] / "cafes.csv"
        processed_file.unlink()
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INCOMPLETE"

    def test_malformed_metadata_incomplete(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        metadata_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "metadata.json"
        metadata_file.write_text("{ invalid json }")
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INCOMPLETE"

    def test_malformed_manifest_integrity_failed(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "manifest.json"
        manifest_file.write_text("{ invalid json }")
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INTEGRITY_FAILED"

    def test_checksum_mismatch_integrity_failed(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["artifacts"][0]["sha256"] = "0" * 64
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INTEGRITY_FAILED"

    def test_schema_violation_integrity_failed(self, snapshot_dirs):
        df = make_valid_df()
        df.loc[0, "osm_id"] = ""  # invalid: empty string
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INTEGRITY_FAILED"

    def test_record_count_mismatch_integrity_failed(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["record_count"] = 999
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "INTEGRITY_FAILED"

    def test_no_snapshots(self, snapshot_dirs):
        # No snapshots exist
        report = integrity.verify_latest()
        assert report["status"] == "NO_SNAPSHOTS"

    def test_no_valid_snapshots(self, snapshot_dirs):
        # Create a snapshot directory but without valid manifest
        snapshot_dirs["raw"].mkdir(parents=True, exist_ok=True)
        (snapshot_dirs["raw"] / "2026-09-13T063235Z").mkdir()
        report = integrity.verify_latest()
        assert report["status"] == "NO_VALID_SNAPSHOTS"

    def test_nonexistent_snapshot(self, snapshot_dirs):
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "SNAPSHOT_NOT_FOUND"

    def test_snapshot_without_manifest(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "manifest.json"
        manifest_file.unlink()
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "NO_MANIFEST"

    def test_snapshot_without_quarantine_no_manifest(self, snapshot_dirs):
        """Missing manifest without quarantine marker -> NO_MANIFEST"""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "manifest.json"
        manifest_file.unlink()
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "NO_MANIFEST"

    def test_snapshot_with_quarantine(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "manifest.json"
        manifest_file.unlink()
        quarantine_file = snapshot_dirs["raw"] / snap["snapshot_id"] / "quarantine.json"
        quarantine_file.write_text(json.dumps({"snapshot_id": snap["snapshot_id"], "reason": "test"}))
        report = integrity.verify_snapshot(snap["snapshot_id"])
        assert report["status"] == "QUARANTINED"

    def test_json_report_validity(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot(snap["snapshot_id"])
        json_str = integrity.report_to_json(report)
        parsed = json.loads(json_str)
        assert parsed["status"] == report["status"]

    def test_human_readable_report(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot(snap["snapshot_id"])
        output = integrity.format_report(report)
        assert "PASSED" in output or "FAILED" in output or "INTEGRITY" in output

    def test_verbose_report(self, snapshot_dirs):
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot(snap["snapshot_id"])
        output = integrity.format_report(report, verbose=True)
        assert "Details" in output


class TestCLI:
    """Tests for CLI behavior."""

    def test_help_exits_zero(self):
        import subprocess
        result = subprocess.run(["python", "-m", "cafe_finder.integrity", "--help"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_default_check_latest(self, snapshot_dirs):
        import subprocess
        df = make_valid_df()
        create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        env = os.environ.copy()
        env["CAFE_FINDER_RAW_SNAPSHOTS_DIR"] = str(snapshot_dirs["raw"])
        env["CAFE_FINDER_PROCESSED_SNAPSHOTS_DIR"] = str(snapshot_dirs["processed"])
        result = subprocess.run(["python", "-m", "cafe_finder.integrity"], capture_output=True, text=True, cwd=snapshot_dirs["tmp"], env=env)
        assert result.returncode == 0

    def test_snapshot_flag(self, snapshot_dirs):
        import subprocess
        df = make_valid_df()
        create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        env = os.environ.copy()
        env["CAFE_FINDER_RAW_SNAPSHOTS_DIR"] = str(snapshot_dirs["raw"])
        env["CAFE_FINDER_PROCESSED_SNAPSHOTS_DIR"] = str(snapshot_dirs["processed"])
        result = subprocess.run(["python", "-m", "cafe_finder.integrity", "--snapshot", "2026-09-13T063235Z"], capture_output=True, text=True, cwd=snapshot_dirs["tmp"], env=env)
        assert result.returncode == 0

    def test_json_output(self, snapshot_dirs):
        import subprocess
        df = make_valid_df()
        create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        env = os.environ.copy()
        env["CAFE_FINDER_RAW_SNAPSHOTS_DIR"] = str(snapshot_dirs["raw"])
        env["CAFE_FINDER_PROCESSED_SNAPSHOTS_DIR"] = str(snapshot_dirs["processed"])
        result = subprocess.run(["python", "-m", "cafe_finder.integrity", "--json"], capture_output=True, text=True, cwd=snapshot_dirs["tmp"], env=env)
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert "status" in parsed

    def test_output_file(self, snapshot_dirs):
        import subprocess
        df = make_valid_df()
        create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        output_file = snapshot_dirs["tmp"] / "report.json"
        env = os.environ.copy()
        env["CAFE_FINDER_RAW_SNAPSHOTS_DIR"] = str(snapshot_dirs["raw"])
        env["CAFE_FINDER_PROCESSED_SNAPSHOTS_DIR"] = str(snapshot_dirs["processed"])
        result = subprocess.run(["python", "-m", "cafe_finder.integrity", "--output", str(output_file)], capture_output=True, text=True, cwd=snapshot_dirs["tmp"], env=env)
        assert result.returncode == 0
        assert output_file.exists()

    def test_invalid_args(self):
        import subprocess
        result = subprocess.run(["python", "-m", "cafe_finder.integrity", "--invalid"], capture_output=True, text=True)
        assert result.returncode == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
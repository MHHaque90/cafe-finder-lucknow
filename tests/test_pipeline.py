"""Tests for pipeline orchestration (Phase 10)."""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from cafe_finder import integrity, manifest, schema, snapshot
from cafe_finder import pipeline


def make_valid_records() -> list[dict]:
    """Create valid records for testing."""
    return [{
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
    }]


def make_valid_df() -> pd.DataFrame:
    """Create a valid DataFrame with all 13 canonical columns."""
    df = pd.DataFrame([{
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
    for col in ["osm_id", "name", "street", "housenumber", "city", "postcode",
                "cuisine", "opening_hours", "website", "phone", "source"]:
        df[col] = df[col].astype(str)
    return df


@pytest.fixture
def snapshot_dirs(tmp_path: Path) -> dict:
    """Create temporary snapshot directories and monkeypatch module-level paths."""
    raw = tmp_path / "raw" / "snapshots"
    processed = tmp_path / "processed" / "snapshots"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)

    import cafe_finder.snapshot as snapshot_mod
    import cafe_finder.integrity as integrity_mod
    import cafe_finder.pipeline as pipeline_mod

    orig_raw = snapshot_mod.SNAPSHOTS_RAW_DIR
    orig_proc = snapshot_mod.SNAPSHOTS_PROCESSED_DIR
    orig_proc_csv = integrity_mod.PROCESSED_CSV_PATH
    orig_pipeline_csv = pipeline_mod.PROCESSED_CSV_PATH

    snapshot_mod.SNAPSHOTS_RAW_DIR = raw
    snapshot_mod.SNAPSHOTS_PROCESSED_DIR = processed
    integrity_mod.PROCESSED_CSV_PATH = tmp_path / "processed" / "lucknow_cafes.csv"
    pipeline_mod.PROCESSED_CSV_PATH = tmp_path / "processed" / "lucknow_cafes.csv"

    yield {"raw": raw, "processed": processed, "tmp": tmp_path}

    snapshot_mod.SNAPSHOTS_RAW_DIR = orig_raw
    snapshot_mod.SNAPSHOTS_PROCESSED_DIR = orig_proc
    integrity_mod.PROCESSED_CSV_PATH = orig_proc_csv
    pipeline_mod.PROCESSED_CSV_PATH = orig_pipeline_csv


def create_complete_snapshot(snapshot_dirs: dict, snapshot_id: str, df: pd.DataFrame) -> dict:
    """Create a complete snapshot with valid manifest using real checksums."""
    raw_dir = snapshot_dirs["raw"]
    processed_dir = snapshot_dirs["processed"]

    snapshot_dir = raw_dir / snapshot_id
    snapshot_dir.mkdir(parents=True)
    processed_snapshot_dir = processed_dir / snapshot_id
    processed_snapshot_dir.mkdir(parents=True)

    raw_file = snapshot_dir / "raw.json"
    raw_file.write_text("[]")

    processed_file = processed_snapshot_dir / "cafes.csv"
    df.to_csv(processed_file, index=False)

    raw_sha = integrity.sha256_file(raw_file)
    processed_sha = integrity.sha256_file(processed_file)

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

    artifacts = [
        {"path": str(raw_file), "sha256": raw_sha, "size_bytes": raw_file.stat().st_size},
        {"path": str(processed_file), "sha256": processed_sha, "size_bytes": processed_file.stat().st_size},
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


class TestRecoveryContracts:
    """Failure-injection tests for pipeline rollback and recovery contracts."""

    @pytest.fixture(autouse=True)
    def _patch_pipeline_dirs(self, snapshot_dirs, monkeypatch):
        """Patch pipeline module paths for all recovery tests."""
        monkeypatch.setattr(pipeline, "PROCESSED_CSV_PATH",
                            snapshot_dirs["tmp"] / "processed" / "lucknow_cafes.csv")
        self.csv_path = pipeline.PROCESSED_CSV_PATH
        self.raw_dir = snapshot_dirs["raw"]
        self.processed_dir = snapshot_dirs["processed"]
        self.tmp = snapshot_dirs["tmp"]

    def _run_pipeline_with_mock_fetch(self, monkeypatch):
        """Run pipeline with mocked fetch returning valid data, assert exit 1."""
        valid_records = make_valid_records()
        monkeypatch.setattr("cafe_finder.fetch.fetch_lucknow_cafes",
                            lambda **kw: valid_records)
        with pytest.raises(SystemExit) as exc_info:
            pipeline.run_pipeline(user_agent="test", timeout=5, snapshot_mode=True)
        assert exc_info.value.code == 1

    def _seed_csv(self, content: bytes = b"osm_id,name\nnode1,Old\n") -> bytes:
        """Write initial CSV, return its bytes for comparison."""
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path.write_bytes(content)
        return content

    def _backup_path(self) -> Path:
        return self.csv_path.with_suffix(".csv.bak")

    def _find_newest_snapshot_id(self) -> str:
        dirs = [d.name for d in self.raw_dir.iterdir() if d.is_dir()]
        dirs.sort(reverse=True)
        assert dirs, "No snapshot dirs created"
        return dirs[0]

    # --- 1. Promotion failure with existing CSV, successful restoration ---
    def test_promotion_failure_restores_csv(self, monkeypatch):
        original_bytes = self._seed_csv()
        monkeypatch.setattr(pipeline, "promote_csv_atomically",
                            lambda records, path: (_ for _ in ()).throw(
                                RuntimeError("disk full")))
        self._run_pipeline_with_mock_fetch(monkeypatch)
        assert self.csv_path.exists(), "CSV should be restored after promotion failure"
        assert self.csv_path.read_bytes() == original_bytes, \
            "Restored CSV must be byte-for-byte identical to original"

    # --- 2. Promotion + restoration failure ---
    def test_promotion_and_restoration_failure(self, monkeypatch):
        original_bytes = self._seed_csv()
        valid_records = make_valid_records()
        monkeypatch.setattr("cafe_finder.fetch.fetch_lucknow_cafes",
                            lambda **kw: valid_records)
        monkeypatch.setattr(pipeline, "promote_csv_atomically",
                            lambda records, path: (_ for _ in ()).throw(
                                RuntimeError("disk full")))
        original_replace = Path.replace
        def fail_replace(self_path, target):
            if str(self_path).endswith(".bak"):
                raise OSError("cannot restore backup")
            return original_replace(self_path, target)
        monkeypatch.setattr(Path, "replace", fail_replace)
        with pytest.raises(SystemExit) as exc_info:
            pipeline.run_pipeline(user_agent="test", timeout=5, snapshot_mode=True)
        assert exc_info.value.code == 1
        assert self._backup_path().exists(), \
            "Backup must remain after RECOVERY_FAILED"
        backup_bytes = self._backup_path().read_bytes()
        assert backup_bytes == original_bytes, \
            "Backup bytes must be unchanged"

    # --- 3. Final manifest validation failure with existing CSV ---
    def test_final_manifest_failure_restores_csv(self, monkeypatch):
        original_bytes = self._seed_csv()
        original_validate = manifest.validate_manifest
        def fail_final_manifest(m):
            r = original_validate(m)
            if r["valid"] and m.get("status") == "success":
                r["valid"] = False
                r["errors"] = ["injected final manifest failure"]
            return r
        monkeypatch.setattr(manifest, "validate_manifest", fail_final_manifest)
        self._run_pipeline_with_mock_fetch(monkeypatch)
        assert self.csv_path.exists(), "CSV should be restored"
        assert self.csv_path.read_bytes() == original_bytes, \
            "Restored CSV must be byte-for-byte identical to original"
        snap_id = self._find_newest_snapshot_id()
        quarantine = self.raw_dir / snap_id / "quarantine.json"
        assert quarantine.exists(), "Quarantine marker must be written"

    # --- 4. Final manifest validation failure, no existing CSV ---
    def test_final_manifest_failure_no_existing_csv(self, monkeypatch):
        assert not self.csv_path.exists()
        original_validate = manifest.validate_manifest
        def fail_final_manifest(m):
            r = original_validate(m)
            if r["valid"] and m.get("status") == "success":
                r["valid"] = False
                r["errors"] = ["injected final manifest failure"]
            return r
        monkeypatch.setattr(manifest, "validate_manifest", fail_final_manifest)
        self._run_pipeline_with_mock_fetch(monkeypatch)
        assert not self.csv_path.exists(), \
            "New CSV must be deleted when no original exists"
        assert not self._backup_path().exists(), \
            "No backup should be created when no original CSV exists"

    # --- 5. Final manifest write failure with existing CSV ---
    def test_final_manifest_write_failure_restores_csv(self, monkeypatch):
        original_bytes = self._seed_csv()
        original_write = manifest.write_manifest
        call_count = {"n": 0}
        def fail_final_write(m, path):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise OSError("disk full writing manifest")
            return original_write(m, path)
        monkeypatch.setattr(manifest, "write_manifest", fail_final_write)
        with pytest.raises(SystemExit) as exc_info:
            pipeline.run_pipeline(user_agent="test", timeout=5, snapshot_mode=True)
        assert exc_info.value.code == 1
        assert self.csv_path.exists(), "CSV should be restored"
        assert self.csv_path.read_bytes() == original_bytes, \
            "Restored CSV must be byte-for-byte identical to original"

    # --- 6. Final manifest write failure with no existing CSV ---
    def test_final_manifest_write_failure_no_existing_csv(self, monkeypatch):
        assert not self.csv_path.exists()
        original_write = manifest.write_manifest
        call_count = {"n": 0}
        def fail_final_write(m, path):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise OSError("disk full writing manifest")
            return original_write(m, path)
        monkeypatch.setattr(manifest, "write_manifest", fail_final_write)
        with pytest.raises(SystemExit) as exc_info:
            pipeline.run_pipeline(user_agent="test", timeout=5, snapshot_mode=True)
        assert exc_info.value.code == 1
        assert not self.csv_path.exists(), \
            "Newly promoted CSV must be deleted"
        assert not self._backup_path().exists(), \
            "No backup should exist when no original CSV"

    # --- 7. Deletion failure recovery test ---
    def test_deletion_failure_reports_recovery_failed(self, monkeypatch):
        assert not self.csv_path.exists()
        original_validate = manifest.validate_manifest
        def fail_final_manifest(m):
            r = original_validate(m)
            if r["valid"] and m.get("status") == "success":
                r["valid"] = False
                r["errors"] = ["injected failure"]
            return r
        monkeypatch.setattr(manifest, "validate_manifest", fail_final_manifest)
        original_unlink = Path.unlink
        def patched_unlink(self_path, **kw):
            if str(self_path) == str(self.csv_path):
                raise OSError("permission denied")
            return original_unlink(self_path, **kw)
        monkeypatch.setattr(Path, "unlink", patched_unlink)
        self._run_pipeline_with_mock_fetch(monkeypatch)
        assert self.csv_path.exists(), \
            "New CSV remains when deletion fails"
        assert not self._backup_path().exists(), \
            "No backup fabricated during deletion failure"

    # --- 8. Existing backup safety test ---
    def test_existing_backup_prevents_overwrite(self, monkeypatch):
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        original_csv_bytes = b"osm_id,name\nnode1,Original\n"
        self.csv_path.write_bytes(original_csv_bytes)
        backup_bytes = b"old,backup,data"
        self._backup_path().write_bytes(backup_bytes)
        self._run_pipeline_with_mock_fetch(monkeypatch)
        assert self._backup_path().exists(), "Backup must not be overwritten"
        assert self._backup_path().read_bytes() == backup_bytes, \
            "Existing backup must be byte-for-byte unchanged"
        assert self.csv_path.read_bytes() == original_csv_bytes, \
            "Current CSV must be unchanged"

    # --- 9. Successful finalization cleanup test ---
    def test_successful_finalization(self, monkeypatch):
        original_bytes = self._seed_csv()
        valid_records = make_valid_records()
        monkeypatch.setattr("cafe_finder.fetch.fetch_lucknow_cafes",
                            lambda **kw: valid_records)
        result = pipeline.run_pipeline(user_agent="test", timeout=5, snapshot_mode=True)
        assert self.csv_path.exists(), "CSV should exist after success"
        assert not self._backup_path().exists(), \
            "Backup must be cleaned up after successful finalization"
        snap_id = self._find_newest_snapshot_id()
        manifest_path = self.raw_dir / snap_id / "manifest.json"
        assert manifest_path.exists(), "Final manifest must be persisted"
        m = json.loads(manifest_path.read_text())
        assert m["status"] == "success"
        assert "completed_at_utc" in m
        assert m["snapshot_id"] == snap_id
        assert isinstance(m["artifacts"], list) and len(m["artifacts"]) == 2
        assert m["schema"]["schema_version"] == schema.SCHEMA_VERSION
        draft_path = self.raw_dir / snap_id / "manifest.json.draft"
        assert not draft_path.exists(), "Draft must be cleaned up"
        manifest_draft_path = self.raw_dir / snap_id / "manifest.json.draft"
        assert not manifest_draft_path.exists()
        validated = manifest.validate_manifest(m)
        assert validated["valid"], f"Manifest validation failed: {validated['errors']}"

    # --- 10. Backup preservation assertion ---
    def test_backup_preserved_after_promotion_failure(self, monkeypatch):
        """Explicitly assert backup exists after failed/uncertain restoration."""
        original_bytes = self._seed_csv()
        monkeypatch.setattr(pipeline, "promote_csv_atomically",
                            lambda records, path: (_ for _ in ()).throw(
                                RuntimeError("disk full")))
        self._run_pipeline_with_mock_fetch(monkeypatch)
        assert self.csv_path.exists(), "CSV restored"
        assert self.csv_path.read_bytes() == original_bytes

    # --- 11. Quarantine on final manifest failure ---
    def test_quarantine_written_on_manifest_failure(self, monkeypatch):
        self._seed_csv()
        original_validate = manifest.validate_manifest
        def fail_final_manifest(m):
            r = original_validate(m)
            if r["valid"] and m.get("status") == "success":
                r["valid"] = False
                r["errors"] = ["injected failure"]
            return r
        monkeypatch.setattr(manifest, "validate_manifest", fail_final_manifest)
        self._run_pipeline_with_mock_fetch(monkeypatch)
        snap_id = self._find_newest_snapshot_id()
        quarantine = self.raw_dir / snap_id / "quarantine.json"
        assert quarantine.exists()
        q = json.loads(quarantine.read_text())
        assert q["snapshot_id"] == snap_id
        assert q["reason"] == "final_manifest_invalid"

    def test_promotion_failure_does_not_falsely_report_recovery_failed(self, monkeypatch, capfd):
        """Regression: successful restoration must NOT print RECOVERY_FAILED."""
        self._seed_csv()
        monkeypatch.setattr(pipeline, "promote_csv_atomically",
                            lambda records, path: (_ for _ in ()).throw(
                                RuntimeError("disk full")))
        with pytest.raises(SystemExit):
            pipeline.run_pipeline(user_agent="test", timeout=5, snapshot_mode=True)
        _, err = capfd.readouterr()
        assert "RECOVERY_FAILED" not in err, \
            "Successful restoration must not falsely report RECOVERY_FAILED"


class TestPipelineSafety:
    """Ensure pipeline test infrastructure does not make real network calls."""

    def test_save_csv_writes_file(self, tmp_path):
        output = tmp_path / "test.csv"
        records = make_valid_records()
        pipeline.save_csv(records, output)
        assert output.exists()
        df = pd.read_csv(output)
        assert len(df) == 1
        assert df.iloc[0]["osm_id"] == "node12345"

    def test_save_csv_uses_canonical_fields(self, tmp_path):
        output = tmp_path / "test.csv"
        records = [{**make_valid_records()[0], "extra_field": "ignored"}]
        pipeline.save_csv(records, output)
        df = pd.read_csv(output)
        assert "extra_field" not in df.columns
        assert list(df.columns) == pipeline.CSV_FIELDS

    def test_promote_csv_atomically(self, tmp_path):
        output = tmp_path / "lucknow_cafes.csv"
        records = make_valid_records()
        pipeline.promote_csv_atomically(records, output)
        assert output.exists()
        df = pd.read_csv(output)
        assert len(df) == 1


class TestStatusMappings:
    """Test that pipeline states map correctly to integrity statuses."""

    def test_no_manifest_gives_no_manifest(self, snapshot_dirs, tmp_path):
        """Snapshot with all artifacts but no manifest -> NO_MANIFEST."""
        raw = snapshot_dirs["raw"]
        processed = snapshot_dirs["processed"]
        snapshot_id = "2026-09-13T063235Z"
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, snapshot_id, df)
        manifest_file = raw / snapshot_id / "manifest.json"
        manifest_file.unlink()
        report = integrity.verify_snapshot(snapshot_id)
        assert report["status"] == "NO_MANIFEST"

    def test_incomplete_snapshot_gives_incomplete(self, snapshot_dirs):
        """Snapshot missing processed file -> INCOMPLETE."""
        raw = snapshot_dirs["raw"]
        processed = snapshot_dirs["processed"]
        snapshot_id = "2026-09-13T063235Z"
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, snapshot_id, df)
        processed_file = processed / snapshot_id / "cafes.csv"
        processed_file.unlink()
        report = integrity.verify_snapshot(snapshot_id)
        assert report["status"] == "INCOMPLETE"


class TestCrashLikeStates:
    """Test various crash-like states and their integrity status."""

    def test_no_snapshots_at_all(self, snapshot_dirs):
        """No snapshot directories exist."""
        report = integrity.verify_latest()
        assert report["status"] in ("NO_SNAPSHOTS", "NO_VALID_SNAPSHOTS")

    def test_final_manifest_plus_leftover_draft(self, snapshot_dirs):
        """Final manifest exists with leftover draft."""
        raw = snapshot_dirs["raw"]
        processed = snapshot_dirs["processed"]
        snapshot_id = "2026-09-13T063235Z"
        df = make_valid_df()
        create_complete_snapshot(snapshot_dirs, snapshot_id, df)

        # Leave a draft file
        draft_path = raw / snapshot_id / "manifest.json.draft"
        draft_path.write_text('{"status": "preparing"}')

        report = integrity.verify_snapshot(snapshot_id)
        assert report["status"] == "PASSED"

    def test_final_manifest_plus_leftover_backup(self, snapshot_dirs, tmp_path):
        """Final manifest exists with leftover backup."""
        backup_path = tmp_path / "processed" / "lucknow_cafes.csv.bak"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes(b"backup")

        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "PASSED"

    def test_quarantine_marker_present(self, snapshot_dirs):
        """Quarantine marker present -> QUARANTINED."""
        raw = snapshot_dirs["raw"]
        snapshot_id = "2026-09-13T063235Z"
        snapshot_dir = raw / snapshot_id
        snapshot_dir.mkdir(parents=True)

        (snapshot_dir / "metadata.json").write_text(json.dumps({
            "status": "success", "snapshot_id": snapshot_id}))
        (snapshot_dir / "quarantine.json").write_text(json.dumps({
            "snapshot_id": snapshot_id, "reason": "test"}))

        report = integrity.verify_snapshot(snapshot_id)
        assert report["status"] == "QUARANTINED"

    def test_missing_final_manifest_no_quarantine(self, snapshot_dirs):
        """Missing final manifest, no quarantine -> NO_MANIFEST."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_file.unlink()
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "NO_MANIFEST"

    def test_existing_malformed_manifest_integrity_failed(self, snapshot_dirs):
        """Malformed final manifest -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_file.write_text("{ invalid json }")
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"

    def test_stale_artifacts_size_mismatch(self, snapshot_dirs):
        """Artifact size mismatch -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["artifacts"][0]["size_bytes"] = 999
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"

    def test_stale_artifacts_checksum_mismatch(self, snapshot_dirs):
        """Artifact checksum mismatch -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["artifacts"][0]["sha256"] = "0" * 64
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"

    def test_record_count_mismatch(self, snapshot_dirs):
        """Record count mismatch -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["record_count"] = 999
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"

    def test_valid_snapshot_passes(self, snapshot_dirs):
        """Complete valid snapshot -> PASSED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "PASSED"

    def test_nonexistent_snapshot(self, snapshot_dirs):
        """Nonexistent snapshot -> SNAPSHOT_NOT_FOUND."""
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "SNAPSHOT_NOT_FOUND"

    def test_quarantined_snapshot(self, snapshot_dirs):
        """Quarantined snapshot -> QUARANTINED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        quarantine_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "quarantine.json"
        quarantine_file.write_text(json.dumps({"snapshot_id": "2026-09-13T063235Z", "reason": "test"}))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "QUARANTINED"

    def test_snapshot_id_mismatch_in_manifest(self, snapshot_dirs):
        """Manifest snapshot_id doesn't match -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["snapshot_id"] = "wrong-id"
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"

    def test_invalid_manifest_status(self, snapshot_dirs):
        """Manifest with wrong status -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["status"] = "preparing"
        del manifest_data["completed_at_utc"]
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"

    def test_missing_artifact_in_manifest(self, snapshot_dirs):
        """Manifest references missing artifact -> INTEGRITY_FAILED."""
        df = make_valid_df()
        snap = create_complete_snapshot(snapshot_dirs, "2026-09-13T063235Z", df)
        manifest_file = snapshot_dirs["raw"] / "2026-09-13T063235Z" / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text())
        manifest_data["artifacts"][0]["path"] = "/nonexistent/path"
        manifest_file.write_text(json.dumps(manifest_data))
        report = integrity.verify_snapshot("2026-09-13T063235Z")
        assert report["status"] == "INTEGRITY_FAILED"


class TestBackupBehavior:
    """Test backup-related pipeline behaviors."""

    def test_backup_exists_aborts(self, snapshot_dirs, monkeypatch):
        """Pipeline should abort if backup file already exists."""
        backup_path = pipeline.PROCESSED_CSV_PATH.parent / "lucknow_cafes.csv.bak"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes(b"old backup")

        valid_records = make_valid_records()
        monkeypatch.setattr("cafe_finder.fetch.fetch_lucknow_cafes",
                            lambda **kw: valid_records)
        with pytest.raises(SystemExit) as exc_info:
            pipeline.run_pipeline(
                user_agent="test",
                timeout=5,
                snapshot_mode=True,
            )
        assert exc_info.value.code == 1
        assert backup_path.exists(), "Existing backup must not be overwritten"
        assert backup_path.read_bytes() == b"old backup"


class TestManifestIntegration:
    """Test manifest creation and validation integration."""

    def test_draft_manifest_validation(self):
        """Draft manifest with valid fields passes validation."""
        draft = {
            "manifest_version": 1,
            "pipeline_name": "cafe_finder",
            "schema_version": 1,
            "status": "preparing",
            "snapshot_id": "2026-09-13T063235Z",
            "started_at_utc": "2026-09-13T06:32:35Z",
            "retrieved_at_utc": "2026-09-13T06:32:40Z",
            "source": "OpenStreetMap",
            "retrieval_method": "Overpass API",
            "endpoint": "https://overpass-api.de/api/interpreter",
            "query": "[out:json];nwr;out;",
            "record_count": 10,
            "artifacts": [{"path": "raw.json", "sha256": "a" * 64, "size_bytes": 100}],
            "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
        }
        result = manifest.validate_manifest_draft(draft)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_draft_manifest_rejects_completed_at_utc(self):
        """Draft manifest with completed_at_utc is invalid."""
        draft = {
            "manifest_version": 1,
            "pipeline_name": "cafe_finder",
            "schema_version": 1,
            "status": "preparing",
            "snapshot_id": "2026-09-13T063235Z",
            "started_at_utc": "2026-09-13T06:32:35Z",
            "retrieved_at_utc": "2026-09-13T06:32:40Z",
            "source": "OpenStreetMap",
            "retrieval_method": "Overpass API",
            "endpoint": "https://overpass-api.de/api/interpreter",
            "query": "[out:json];nwr;out;",
            "record_count": 10,
            "artifacts": [{"path": "raw.json", "sha256": "a" * 64, "size_bytes": 100}],
            "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
            "completed_at_utc": "2026-09-13T06:32:41Z",
        }
        result = manifest.validate_manifest_draft(draft)
        assert result["valid"] is False

    def test_final_manifest_validation(self):
        """Final manifest with valid fields passes validation."""
        final = {
            "manifest_version": 1,
            "pipeline_name": "cafe_finder",
            "schema_version": 1,
            "status": "success",
            "snapshot_id": "2026-09-13T063235Z",
            "started_at_utc": "2026-09-13T06:32:35Z",
            "retrieved_at_utc": "2026-09-13T06:32:40Z",
            "source": "OpenStreetMap",
            "retrieval_method": "Overpass API",
            "endpoint": "https://overpass-api.de/api/interpreter",
            "query": "[out:json];nwr;out;",
            "record_count": 10,
            "artifacts": [{"path": "raw.json", "sha256": "a" * 64, "size_bytes": 100}],
            "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
            "completed_at_utc": "2026-09-13T06:32:41Z",
        }
        result = manifest.validate_manifest(final)
        assert result["valid"] is True

    def test_final_manifest_rejects_wrong_status(self):
        """Final manifest with wrong status is invalid."""
        final = {
            "manifest_version": 1,
            "pipeline_name": "cafe_finder",
            "schema_version": 1,
            "status": "preparing",
            "snapshot_id": "2026-09-13T063235Z",
            "started_at_utc": "2026-09-13T06:32:35Z",
            "retrieved_at_utc": "2026-09-13T06:32:40Z",
            "source": "OpenStreetMap",
            "retrieval_method": "Overpass API",
            "endpoint": "https://overpass-api.de/api/interpreter",
            "query": "[out:json];nwr;out;",
            "record_count": 10,
            "artifacts": [{"path": "raw.json", "sha256": "a" * 64, "size_bytes": 100}],
            "schema": {"schema_version": 1, "columns": schema.CANONICAL_COLUMNS, "required": schema.REQUIRED_COLUMNS},
            "completed_at_utc": "2026-09-13T06:32:41Z",
        }
        result = manifest.validate_manifest(final)
        assert result["valid"] is False


class TestSchemaIntegration:
    """Test schema validation integration with pipeline."""

    def test_valid_schema_passes(self):
        """Valid DataFrame passes schema validation."""
        df = make_valid_df()
        result = schema.validate_schema(df)
        assert result["valid"] is True

    def test_missing_column_fails(self):
        """DataFrame missing a column fails schema validation."""
        df = make_valid_df().drop(columns=["cuisine"])
        result = schema.validate_schema(df)
        assert result["valid"] is False

    def test_invalid_osm_id_fails(self):
        """DataFrame with invalid osm_id fails schema validation."""
        df = make_valid_df()
        df.loc[0, "osm_id"] = ""
        result = schema.validate_schema(df)
        assert result["valid"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

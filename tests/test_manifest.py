"""Tests for manifest creation and validation (Phase 10)."""

import json
import tempfile
from pathlib import Path

import pytest

from cafe_finder.manifest import (
    MANIFEST_VERSION,
    PIPELINE_NAME,
    SCHEMA_VERSION,
    CANONICAL_COLUMNS,
    REQUIRED_COLUMNS,
    build_manifest_draft,
    build_manifest,
    validate_manifest_draft,
    validate_manifest,
    write_manifest,
    load_manifest,
    serialize_manifest,
    ManifestError,
)


def make_draft() -> dict:
    """Create a valid draft manifest."""
    return build_manifest_draft(
        snapshot_id="2026-09-13T063235Z",
        started_at_utc="2026-09-13T06:32:35Z",
        retrieved_at_utc="2026-09-13T06:32:40Z",
        endpoint="https://overpass-api.de/api/interpreter",
        query="[out:json];nwr;out;",
        record_count=33,
        artifacts=[
            {"path": "data/raw/snapshots/2026-09-13T063235Z/raw.json", "sha256": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6abcd", "size_bytes": 10240},
            {"path": "data/processed/snapshots/2026-09-13T063235Z/cafes.csv", "sha256": "deadbeef1234deadbeef1234deadbeef1234deadbeef1234deadbeef1234abcd", "size_bytes": 20480},
        ],
        schema_result={"valid": True, "schema_version": 1, "missing_columns": [], "unexpected_columns": [], "invalid_types": {}, "column_order_valid": True},
    )


def make_final_manifest() -> dict:
    """Create a valid final manifest."""
    draft = make_draft()
    return build_manifest(draft, "2026-09-13T06:32:41Z")


class TestManifestDraft:
    """Tests for draft manifest creation and validation."""

    def test_valid_draft_creation(self):
        draft = make_draft()
        assert draft["manifest_version"] == MANIFEST_VERSION
        assert draft["pipeline_name"] == PIPELINE_NAME
        assert draft["schema_version"] == SCHEMA_VERSION
        assert draft["status"] == "preparing"
        assert "completed_at_utc" not in draft
        assert draft["snapshot_id"] == "2026-09-13T063235Z"
        assert draft["started_at_utc"] == "2026-09-13T06:32:35Z"
        assert draft["retrieved_at_utc"] == "2026-09-13T06:32:40Z"
        assert draft["source"] == "OpenStreetMap"
        assert draft["retrieval_method"] == "Overpass API"
        assert draft["endpoint"] == "https://overpass-api.de/api/interpreter"
        assert draft["query"] == "[out:json];nwr;out;"
        assert draft["record_count"] == 33
        assert len(draft["artifacts"]) == 2
        assert draft["schema"]["schema_version"] == SCHEMA_VERSION
        assert draft["schema"]["columns"] == CANONICAL_COLUMNS
        assert draft["schema"]["required"] == REQUIRED_COLUMNS

    def test_draft_validator_accepts_valid_draft(self):
        draft = make_draft()
        result = validate_manifest_draft(draft)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_draft_validator_rejects_completed_at_utc(self):
        draft = make_draft()
        draft["completed_at_utc"] = "2026-09-13T06:32:41Z"
        result = validate_manifest_draft(draft)
        assert result["valid"] is False
        assert any("completed_at_utc" in e for e in result["errors"])

    def test_draft_validator_rejects_wrong_status(self):
        draft = make_draft()
        draft["status"] = "success"
        result = validate_manifest_draft(draft)
        assert result["valid"] is False
        assert any("status" in e for e in result["errors"])


class TestManifestFinal:
    """Tests for final manifest creation and validation."""

    def test_valid_final_creation(self):
        final = make_final_manifest()
        assert final["status"] == "success"
        assert final["completed_at_utc"] == "2026-09-13T06:32:41Z"
        assert final["manifest_version"] == MANIFEST_VERSION

    def test_final_validator_requires_completed_at_utc(self):
        final = make_final_manifest()
        del final["completed_at_utc"]
        result = validate_manifest(final)
        assert result["valid"] is False
        assert any("completed_at_utc" in e for e in result["errors"])

    def test_final_validator_requires_success_status(self):
        final = make_final_manifest()
        final["status"] = "preparing"
        result = validate_manifest(final)
        assert result["valid"] is False
        assert any("status" in e for e in result["errors"])

    def test_final_validator_rejects_invalid_timestamp(self):
        final = make_final_manifest()
        final["completed_at_utc"] = "not-a-timestamp"
        result = validate_manifest(final)
        assert result["valid"] is False
        assert any("completed_at_utc" in e for e in result["errors"])


class TestManifestValidation:
    """Tests for manifest validation edge cases."""

    def test_missing_required_field_rejected(self):
        draft = make_draft()
        del draft["snapshot_id"]
        result = validate_manifest_draft(draft)
        assert result["valid"] is False
        assert any("snapshot_id" in e for e in result["errors"])

    def test_invalid_manifest_version_rejected(self):
        draft = make_draft()
        draft["manifest_version"] = 2
        result = validate_manifest_draft(draft)
        assert result["valid"] is False

    def test_invalid_schema_version_rejected(self):
        draft = make_draft()
        draft["schema_version"] = 2
        result = validate_manifest_draft(draft)
        assert result["valid"] is False

    def test_negative_record_count_rejected(self):
        draft = make_draft()
        draft["record_count"] = -1
        result = validate_manifest_draft(draft)
        assert result["valid"] is False

    def test_non_integer_record_count_rejected(self):
        draft = make_draft()
        draft["record_count"] = 3.14
        result = validate_manifest_draft(draft)
        assert result["valid"] is False

    def test_artifact_metadata_validation(self):
        draft = make_draft()
        draft["artifacts"][0]["sha256"] = "GHIJKL"  # uppercase
        result = validate_manifest_draft(draft)
        assert result["valid"] is False
        assert any("sha256" in e for e in result["errors"])

        draft = make_draft()
        draft["artifacts"][0]["sha256"] = "abc"  # too short
        result = validate_manifest_draft(draft)
        assert result["valid"] is False

        draft = make_draft()
        draft["artifacts"][0]["size_bytes"] = -1
        result = validate_manifest_draft(draft)
        assert result["valid"] is False

    def test_malformed_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            path = Path(f.name)
        try:
            with pytest.raises(Exception):
                from cafe_finder.manifest import load_manifest
                load_manifest(path)
        finally:
            path.unlink(missing_ok=True)

    def test_missing_required_field_in_final(self):
        final = make_final_manifest()
        del final["schema"]
        result = validate_manifest(final)
        assert result["valid"] is False
        assert any("schema" in e for e in result["errors"])

    def test_deterministic_serialization(self):
        draft = make_draft()
        ser1 = serialize_manifest(draft)
        ser2 = serialize_manifest(draft)
        assert ser1 == ser2
        # Check keys are sorted
        parsed = json.loads(ser1)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_no_self_referential_checksum(self):
        final = make_final_manifest()
        # Manifest should not contain its own checksum
        serialized = serialize_manifest(final)
        assert "checksum" not in serialized.lower()
        assert "sha256" not in final  # manifest itself doesn't have sha256


class TestManifestIO:
    """Tests for manifest write/load operations."""

    def test_write_and_load_manifest(self):
        final = make_final_manifest()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            write_manifest(final, path)
            loaded = load_manifest(path)
            assert loaded == final
        finally:
            path.unlink(missing_ok=True)

    def test_write_manifest_creates_parents(self):
        final = make_final_manifest()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "manifest.json"
            write_manifest(final, path)
            assert path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
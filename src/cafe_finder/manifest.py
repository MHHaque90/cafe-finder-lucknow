"""Manifest creation, validation, and serialization for Lucknow Cafe Finder."""

import json
import os
from pathlib import Path
from typing import Any

from . import schema

MANIFEST_VERSION = 1
PIPELINE_NAME = "cafe_finder"

# Re-export from schema for convenience
SCHEMA_VERSION = schema.SCHEMA_VERSION
CANONICAL_COLUMNS = schema.CANONICAL_COLUMNS
REQUIRED_COLUMNS = schema.REQUIRED_COLUMNS


class ManifestError(Exception):
    """Raised when manifest operations fail."""
    pass


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_artifact_entry(file_path: Path, display_path: str) -> dict[str, Any]:
    """
    Compute artifact metadata entry for a file.

    Args:
        file_path: Path to the file
        display_path: Path to store in manifest (relative to project root)

    Returns:
        Dictionary with path, sha256, and size_bytes
    """
    if not file_path.exists():
        raise ManifestError(f"Artifact file not found: {file_path}")
    sha256 = _sha256_file(file_path)
    size = file_path.stat().st_size
    return {
        "path": display_path,
        "sha256": sha256,
        "size_bytes": size,
    }


def build_manifest_draft(
    snapshot_id: str,
    started_at_utc: str,
    retrieved_at_utc: str,
    endpoint: str,
    query: str,
    record_count: int,
    artifacts: list[dict[str, Any]],
    schema_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a draft manifest (pre-promotion, no completed_at_utc).

    Args:
        snapshot_id: Snapshot identifier
        started_at_utc: Pipeline start timestamp
        retrieved_at_utc: Retrieval timestamp
        endpoint: Overpass endpoint URL
        query: Overpass query string
        record_count: Number of records
        artifacts: List of artifact entries
        schema_result: Result from schema.validate_schema()

    Returns:
        Draft manifest dictionary
    """
    return {
        "manifest_version": MANIFEST_VERSION,
        "pipeline_name": PIPELINE_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "preparing",
        "snapshot_id": snapshot_id,
        "started_at_utc": started_at_utc,
        "retrieved_at_utc": retrieved_at_utc,
        "source": "OpenStreetMap",
        "retrieval_method": "Overpass API",
        "endpoint": endpoint,
        "query": query,
        "record_count": record_count,
        "artifacts": artifacts,
        "schema": {
            "schema_version": SCHEMA_VERSION,
            "columns": CANONICAL_COLUMNS,
            "required": REQUIRED_COLUMNS,
        },
    }


def build_manifest(
    draft: dict[str, Any],
    completed_at_utc: str,
) -> dict[str, Any]:
    """
    Build final manifest from draft by adding completed_at_utc and status.

    Args:
        draft: Draft manifest from build_manifest_draft()
        completed_at_utc: Completion timestamp

    Returns:
        Final manifest dictionary
    """
    return {
        **draft,
        "status": "success",
        "completed_at_utc": completed_at_utc,
    }


def validate_manifest_draft(draft: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a draft manifest (no completed_at_utc required, status=preparing).

    Args:
        draft: Draft manifest dictionary

    Returns:
        Validation result: {"valid": bool, "errors": list[str]}
    """
    errors = []

    required_keys = [
        "manifest_version", "pipeline_name", "schema_version", "status",
        "snapshot_id", "started_at_utc", "retrieved_at_utc",
        "source", "retrieval_method", "endpoint", "query",
        "record_count", "artifacts", "schema"
    ]

    for key in required_keys:
        if key not in draft:
            errors.append(f"Missing required field: {key}")

    if "manifest_version" in draft and draft["manifest_version"] != MANIFEST_VERSION:
        errors.append(f"Invalid manifest_version: expected {MANIFEST_VERSION}, got {draft['manifest_version']}")

    if "pipeline_name" in draft and draft["pipeline_name"] != PIPELINE_NAME:
        errors.append(f"Invalid pipeline_name: expected '{PIPELINE_NAME}', got '{draft['pipeline_name']}'")

    if "schema_version" in draft and draft["schema_version"] != SCHEMA_VERSION:
        errors.append(f"Invalid schema_version: expected {SCHEMA_VERSION}, got {draft['schema_version']}")

    if "status" in draft and draft["status"] != "preparing":
        errors.append(f"Invalid status: expected 'preparing', got '{draft['status']}'")

    if "completed_at_utc" in draft:
        errors.append("Draft manifest must not contain completed_at_utc")

    if "snapshot_id" in draft and not isinstance(draft["snapshot_id"], str):
        errors.append("snapshot_id must be string")

    if "record_count" in draft:
        if not isinstance(draft["record_count"], int) or draft["record_count"] < 0:
            errors.append("record_count must be non-negative integer")

    if "artifacts" in draft:
        if not isinstance(draft["artifacts"], list) or len(draft["artifacts"]) == 0:
            errors.append("artifacts must be non-empty list")
        else:
            for i, artifact in enumerate(draft["artifacts"]):
                if not isinstance(artifact, dict):
                    errors.append(f"artifact[{i}] must be object")
                    continue
                for field in ["path", "sha256", "size_bytes"]:
                    if field not in artifact:
                        errors.append(f"artifact[{i}] missing field: {field}")
                if "sha256" in artifact:
                    sha = artifact["sha256"]
                    if not isinstance(sha, str) or len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
                        errors.append(f"artifact[{i}] sha256 must be 64-char lowercase hex")
                if "size_bytes" in artifact:
                    if not isinstance(artifact["size_bytes"], int) or artifact["size_bytes"] < 0:
                        errors.append(f"artifact[{i}] size_bytes must be non-negative integer")

    if "schema" in draft:
        sch = draft["schema"]
        if not isinstance(sch, dict):
            errors.append("schema must be object")
        else:
            if sch.get("schema_version") != SCHEMA_VERSION:
                errors.append(f"schema.schema_version must be {SCHEMA_VERSION}")
            if "columns" not in sch or sch["columns"] != CANONICAL_COLUMNS:
                errors.append("schema.columns must match canonical columns")
            if "required" not in sch or sch["required"] != REQUIRED_COLUMNS:
                errors.append("schema.required must match required columns")

    return {"valid": len(errors) == 0, "errors": errors}


def _validate_manifest_common(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate common fields for both draft and final manifests."""
    errors = []

    required_keys = [
        "manifest_version", "pipeline_name", "schema_version", "status",
        "snapshot_id", "started_at_utc", "retrieved_at_utc",
        "source", "retrieval_method", "endpoint", "query",
        "record_count", "artifacts", "schema"
    ]

    for key in required_keys:
        if key not in manifest:
            errors.append(f"Missing required field: {key}")

    if "manifest_version" in manifest and manifest["manifest_version"] != MANIFEST_VERSION:
        errors.append(f"Invalid manifest_version: expected {MANIFEST_VERSION}, got {manifest['manifest_version']}")

    if "pipeline_name" in manifest and manifest["pipeline_name"] != PIPELINE_NAME:
        errors.append(f"Invalid pipeline_name: expected '{PIPELINE_NAME}', got '{manifest['pipeline_name']}'")

    if "schema_version" in manifest and manifest["schema_version"] != SCHEMA_VERSION:
        errors.append(f"Invalid schema_version: expected {SCHEMA_VERSION}, got {manifest['schema_version']}")

    if "snapshot_id" in manifest and not isinstance(manifest["snapshot_id"], str):
        errors.append("snapshot_id must be string")

    if "record_count" in manifest:
        if not isinstance(manifest["record_count"], int) or manifest["record_count"] < 0:
            errors.append("record_count must be non-negative integer")

    if "artifacts" in manifest:
        if not isinstance(manifest["artifacts"], list) or len(manifest["artifacts"]) == 0:
            errors.append("artifacts must be non-empty list")
        else:
            for i, artifact in enumerate(manifest["artifacts"]):
                if not isinstance(artifact, dict):
                    errors.append(f"artifact[{i}] must be object")
                    continue
                for field in ["path", "sha256", "size_bytes"]:
                    if field not in artifact:
                        errors.append(f"artifact[{i}] missing field: {field}")
                if "sha256" in artifact:
                    sha = artifact["sha256"]
                    if not isinstance(sha, str) or len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
                        errors.append(f"artifact[{i}] sha256 must be 64-char lowercase hex")
                if "size_bytes" in artifact:
                    if not isinstance(artifact["size_bytes"], int) or artifact["size_bytes"] < 0:
                        errors.append(f"artifact[{i}] size_bytes must be non-negative integer")

    if "schema" in manifest:
        sch = manifest["schema"]
        if not isinstance(sch, dict):
            errors.append("schema must be object")
        else:
            if sch.get("schema_version") != SCHEMA_VERSION:
                errors.append(f"schema.schema_version must be {SCHEMA_VERSION}")
            if "columns" not in sch or sch["columns"] != CANONICAL_COLUMNS:
                errors.append("schema.columns must match canonical columns")
            if "required" not in sch or sch["required"] != REQUIRED_COLUMNS:
                errors.append("schema.required must match required columns")

    return {"valid": len(errors) == 0, "errors": errors}


def validate_manifest_draft(draft: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a draft manifest (no completed_at_utc required, status=preparing).

    Args:
        draft: Draft manifest dictionary

    Returns:
        Validation result: {"valid": bool, "errors": list[str]}
    """
    result = _validate_manifest_common(draft)

    if not result["valid"]:
        return result

    if "status" in draft and draft["status"] != "preparing":
        result["errors"].append(f"Invalid status: expected 'preparing', got '{draft['status']}'")
        result["valid"] = False

    if "completed_at_utc" in draft:
        result["errors"].append("Draft manifest must not contain completed_at_utc")
        result["valid"] = False

    return result


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a final manifest (requires completed_at_utc, status=success).

    Args:
        manifest: Final manifest dictionary

    Returns:
        Validation result: {"valid": bool, "errors": list[str]}
    """
    result = _validate_manifest_common(manifest)

    if not result["valid"]:
        return result

    if manifest.get("status") != "success":
        result["errors"].append(f"Invalid status: expected 'success', got '{manifest.get('status')}'")
        result["valid"] = False

    if "completed_at_utc" not in manifest:
        result["errors"].append("Missing required field: completed_at_utc")
        result["valid"] = False
    else:
        ts = manifest["completed_at_utc"]
        if not isinstance(ts, str):
            result["errors"].append("completed_at_utc must be string")
            result["valid"] = False
        else:
            try:
                from datetime import datetime
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                result["errors"].append("completed_at_utc must be valid ISO-8601 timestamp")
                result["valid"] = False

    return result


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    """
    Write manifest to file atomically.

    Args:
        manifest: Manifest dictionary
        path: Destination path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
    temp_path.replace(path)


def load_manifest(path: Path) -> dict[str, Any]:
    """
    Load manifest from file.

    Args:
        path: Manifest file path

    Returns:
        Manifest dictionary

    Raises:
        ManifestError: If file not found, unreadable, or malformed JSON
    """
    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"Malformed JSON in manifest: {e}")
    except OSError as e:
        raise ManifestError(f"Cannot read manifest: {e}")


def serialize_manifest(manifest: dict[str, Any]) -> str:
    """
    Serialize manifest to deterministic JSON string.

    Args:
        manifest: Manifest dictionary

    Returns:
        JSON string with sorted keys
    """
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    """Command-line entry point for manifest validation."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Manifest Validation"
    )
    parser.add_argument(
        "manifest_path",
        help="Path to manifest file to validate",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Validate as draft manifest (no completed_at_utc required)",
    )
    args = parser.parse_args()

    from pathlib import Path
    manifest_path = Path(args.manifest_path)

    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.draft:
        result = validate_manifest_draft(manifest)
    else:
        result = validate_manifest(manifest)

    if result["valid"]:
        print("Manifest validation: PASSED")
        sys.exit(0)
    else:
        print("Manifest validation: FAILED", file=sys.stderr)
        for error in result["errors"]:
            print(f"  {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
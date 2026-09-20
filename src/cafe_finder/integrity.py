"""Integrity verification and SHA-256 checksums for Lucknow Cafe Finder."""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from cafe_finder.config import PROCESSED_DIR
from . import manifest, schema, snapshot

PROCESSED_CSV_PATH = PROCESSED_DIR / "lucknow_cafes.csv"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifact(path: Path, expected_sha256: str | None, expected_size: int | None) -> dict[str, Any]:
    """
    Verify a single artifact file.

    Args:
        path: Path to the artifact file
        expected_sha256: Expected SHA-256 checksum (or None to skip)
        expected_size: Expected file size in bytes (or None to skip)

    Returns:
        Verification result dictionary
    """
    result = {
        "path": str(path),
        "exists": path.exists(),
        "readable": False,
        "sha256_actual": None,
        "sha256_expected": expected_sha256,
        "sha_match": None,
        "size_actual": None,
        "size_expected": expected_size,
        "size_match": None,
        "valid": False,
        "error": None,
    }

    if not path.exists():
        result["error"] = "File does not exist"
        return result

    try:
        with path.open("rb"):
            result["readable"] = True
    except OSError as e:
        result["error"] = f"File not readable: {e}"
        return result

    try:
        result["sha256_actual"] = sha256_file(path)
        result["size_actual"] = path.stat().st_size
    except OSError as e:
        result["error"] = f"Cannot read file: {e}"
        return result

    if expected_sha256 is not None:
        result["sha_match"] = (result["sha256_actual"] == expected_sha256)
        if not result["sha_match"]:
            result["error"] = "Checksum mismatch"

    if expected_size is not None:
        result["size_match"] = (result["size_actual"] == expected_size)
        if not result["size_match"]:
            result["error"] = "Size mismatch"

    result["valid"] = (
        result["readable"]
        and (expected_sha256 is None or result["sha_match"])
        and (expected_size is None or result["size_match"])
    )

    return result


def _load_snapshot_metadata(snapshot_id: str) -> dict[str, Any] | None:
    """Load snapshot metadata with quarantine check (discovery only)."""
    return snapshot.load_snapshot_metadata(snapshot_id, require_manifest=True)


def verify_snapshot(snapshot_id: str) -> dict[str, Any]:
    """
    Perform full integrity verification on a snapshot.

    Args:
        snapshot_id: Snapshot identifier

    Returns:
        Verification report dictionary
    """
    report = {
        "snapshot_id": snapshot_id,
        "status": "PASSED",
        "checks": [],
        "errors": [],
    }

    paths = snapshot.get_snapshot_paths(snapshot_id)

    # 1. Snapshot directory exists
    if not paths["raw_dir"].exists():
        report["status"] = "SNAPSHOT_NOT_FOUND"
        report["errors"].append("Snapshot directory does not exist")
        return report

    # 2. Explicit quarantine marker
    if paths["quarantine_file"].exists():
        report["status"] = "QUARANTINED"
        report["errors"].append("Explicit quarantine marker exists")
        return report

    # 3. Metadata existence and readability
    if not paths["metadata_file"].exists():
        report["status"] = "INCOMPLETE"
        report["errors"].append("Metadata file missing or unreadable")
        return report

    try:
        with paths["metadata_file"].open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError):
        report["status"] = "INCOMPLETE"
        report["errors"].append("Metadata file unreadable or malformed")
        return report

    # 4. Required artifacts
    if not paths["raw_file"].exists() or not paths["processed_file"].exists():
        report["status"] = "INCOMPLETE"
        report["errors"].append("Required artifact missing")
        return report

    # 5. Final manifest existence
    if not paths["manifest_file"].exists():
        report["status"] = "NO_MANIFEST"
        report["errors"].append("Final manifest.json missing")
        return report

    # 6. Final manifest readability and parse
    try:
        with paths["manifest_file"].open("r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append("Final manifest unreadable or malformed")
        return report

    # 7. Final manifest contract validation
    manifest_validation = manifest.validate_manifest(manifest_data)
    if not manifest_validation["valid"]:
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].extend([f"Manifest contract: {e}" for e in manifest_validation["errors"]])
        return report

    # 8. Snapshot ID consistency
    if manifest_data.get("snapshot_id") != snapshot_id:
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append("Manifest snapshot_id mismatch")
        return report
    if metadata.get("snapshot_id") != snapshot_id:
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append("Metadata snapshot_id mismatch")
        return report

    # 9. Artifact sizes
    for artifact in manifest_data.get("artifacts", []):
        art_path = Path(artifact["path"])
        if not art_path.exists():
            report["status"] = "INTEGRITY_FAILED"
            report["errors"].append(f"Artifact missing: {artifact['path']}")
            return report
        actual_size = art_path.stat().st_size
        if actual_size != artifact["size_bytes"]:
            report["status"] = "INTEGRITY_FAILED"
            report["errors"].append(f"Size mismatch for {artifact['path']}")
            return report

    # 10. SHA-256 checksums
    for artifact in manifest_data.get("artifacts", []):
        art_path = Path(artifact["path"])
        actual_sha = sha256_file(art_path)
        if actual_sha != artifact["sha256"]:
            report["status"] = "INTEGRITY_FAILED"
            report["errors"].append(f"Checksum mismatch for {artifact['path']}")
            return report

    # 11. Processed CSV schema
    try:
        # Read with explicit dtypes to prevent pandas from inferring numeric types for string columns
        string_columns = {"osm_id", "name", "street", "housenumber", "city", "postcode", "cuisine", "opening_hours", "website", "phone", "source"}
        dtype_map = {col: str for col in string_columns}
        df = pd.read_csv(paths["processed_file"], encoding="utf-8", dtype=dtype_map)
        schema_result = schema.validate_schema(df)
        if not schema_result["valid"]:
            report["status"] = "INTEGRITY_FAILED"
            report["errors"].append(f"Schema validation failed: {schema_result}")
            return report
    except Exception as e:
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append(f"Failed to read or validate processed CSV: {e}")
        return report

    # 12. Record counts
    actual_count = len(df)
    if metadata.get("record_count") != actual_count:
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append(f"Metadata record count mismatch: {metadata.get('record_count')} vs {actual_count}")
        return report
    if manifest_data.get("record_count") != actual_count:
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append(f"Manifest record count mismatch: {manifest_data.get('record_count')} vs {actual_count}")
        return report

    # 13. Cross-file ID consistency
    if metadata.get("snapshot_id") != manifest_data.get("snapshot_id"):
        report["status"] = "INTEGRITY_FAILED"
        report["errors"].append("Metadata/manifest snapshot_id mismatch")
        return report

    report["status"] = "PASSED"
    return report


def verify_latest() -> dict[str, Any]:
    """Verify the latest snapshot (including quarantined)."""
    snapshots_raw_dir = snapshot.SNAPSHOTS_RAW_DIR
    if not snapshots_raw_dir.exists():
        return {"status": "NO_SNAPSHOTS", "errors": ["No snapshot directories exist"]}

    snapshot_dirs = [d for d in snapshots_raw_dir.iterdir() if d.is_dir()]
    if not snapshot_dirs:
        return {"status": "NO_SNAPSHOTS", "errors": ["No snapshot directories exist"]}

    # Sort by snapshot_id (newest first)
    snapshot_dirs.sort(key=lambda d: d.name, reverse=True)

    # Check each snapshot from newest to oldest
    for snapshot_dir in snapshot_dirs:
        snapshot_id = snapshot_dir.name
        # Check for quarantine marker first
        quarantine_file = snapshot_dir / "quarantine.json"
        if quarantine_file.exists():
            return verify_snapshot(snapshot_dir.name)
        # Check if it's a valid snapshot (has final manifest)
        manifest_file = snapshot_dir / "manifest.json"
        if manifest_file.exists():
            return verify_snapshot(snapshot_dir.name)

    # No valid snapshots found, but directories exist
    return {"status": "NO_VALID_SNAPSHOTS", "errors": ["No valid snapshots found"]}


def format_report(report: dict[str, Any], verbose: bool = False) -> str:
    """Format integrity report for human-readable output."""
    lines = []
    lines.append("=" * 50)
    lines.append("INTEGRITY VERIFICATION REPORT")
    lines.append("=" * 50)
    lines.append(f"\nSnapshot ID: {report.get('snapshot_id', 'N/A')}")
    lines.append(f"Status: {report.get('status', 'UNKNOWN')}")

    if verbose:
        lines.append("\nDetails:")
        if report.get("errors"):
            for error in report["errors"]:
                lines.append(f"  - {error}")
        else:
            lines.append("  No issues found")

    if verbose and report.get("checks"):
        lines.append("\nChecks performed:")
        for check in report["checks"]:
            lines.append(f"  - {check}")

    return "\n".join(lines)


def report_to_json(report: dict[str, Any]) -> str:
    """Serialize report to JSON."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    """Command-line entry point for integrity verification."""
    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Integrity Verification"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed diagnostics",
    )
    parser.add_argument(
        "--snapshot",
        help="Snapshot ID to verify",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only",
    )
    parser.add_argument(
        "--output",
        help="Write report to file",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse exits with code 2 for invalid arguments; convert to 1
        if e.code == 2:
            sys.exit(1)
        raise

    if args.snapshot:
        report = verify_snapshot(args.snapshot)
    else:
        report = verify_latest()

    if args.json:
        output = report_to_json(report)
        print(output)
    else:
        output = format_report(report, verbose=args.verbose)
        print(output)

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                f.write(report_to_json(report))
        except OSError as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            sys.exit(1)

    if report.get("status") == "PASSED":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
"""Snapshot management for Lucknow Cafe Finder data refresh workflow."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import fetch

# Allow override via environment variables for testing
_raw_dir_env = os.environ.get("CAFE_FINDER_RAW_SNAPSHOTS_DIR")
_processed_dir_env = os.environ.get("CAFE_FINDER_PROCESSED_SNAPSHOTS_DIR")

SNAPSHOTS_RAW_DIR = Path(_raw_dir_env) if _raw_dir_env else Path("data/raw/snapshots")
SNAPSHOTS_PROCESSED_DIR = Path(_processed_dir_env) if _processed_dir_env else Path("data/processed/snapshots")

REQUIRED_METADATA_KEYS = [
    "snapshot_id",
    "retrieved_at_utc",
    "source",
    "retrieval_method",
    "endpoint",
    "query",
    "record_count",
    "raw_file",
    "processed_file",
    "status",
]

_SUCCESS_STATUS = "success"


def generate_snapshot_id() -> str:
    """
    Generate a filesystem-safe UTC timestamp for snapshot identification.

    Format: YYYY-MM-DDTHHMMSSZ (e.g., 2026-09-08T120000Z)

    Returns:
        Snapshot ID string
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def get_snapshot_paths(snapshot_id: str) -> dict[str, Path]:
    """
    Get all filesystem paths for a given snapshot ID.

    Args:
        snapshot_id: Snapshot identifier

    Returns:
        Dictionary with raw_dir, processed_dir, raw_file, processed_file, metadata_file,
        manifest_file, manifest_draft_file, quarantine_file
    """
    raw_dir = SNAPSHOTS_RAW_DIR / snapshot_id
    processed_dir = SNAPSHOTS_PROCESSED_DIR / snapshot_id

    return {
        "raw_dir": raw_dir,
        "processed_dir": processed_dir,
        "raw_file": raw_dir / "raw.json",
        "processed_file": processed_dir / "cafes.csv",
        "metadata_file": raw_dir / "metadata.json",
        "manifest_file": raw_dir / "manifest.json",
        "manifest_draft_file": raw_dir / "manifest.json.draft",
        "quarantine_file": raw_dir / "quarantine.json",
    }


def generate_metadata(
    snapshot_id: str,
    retrieved_at_utc: str,
    record_count: int,
    query: str,
    raw_file: str,
    processed_file: str,
    status: str = _SUCCESS_STATUS,
) -> dict[str, Any]:
    """
    Generate snapshot metadata.

    Args:
        snapshot_id: Snapshot identifier
        retrieved_at_utc: Actual retrieval timestamp (ISO format, UTC)
        record_count: Number of records in the finalized dataset
        query: Overpass query used
        raw_file: Raw snapshot filename
        processed_file: Processed snapshot filename
        status: Snapshot status ("success" or "failed")

    Returns:
        Metadata dictionary
    """
    return {
        "snapshot_id": snapshot_id,
        "retrieved_at_utc": retrieved_at_utc,
        "source": "OpenStreetMap",
        "retrieval_method": "Overpass API",
        "endpoint": fetch.OVERPASS_URL,
        "query": query,
        "record_count": record_count,
        "raw_file": raw_file,
        "processed_file": processed_file,
        "status": status,
    }


def _write_metadata(path: Path, metadata: dict[str, Any]) -> None:
    """Write metadata to a JSON file."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def save_raw_snapshot(
    records: list[dict[str, Any]],
    snapshot_id: str,
    retrieved_at_utc: str,
    query: str,
) -> Path:
    """
    Save raw snapshot with metadata.

    Args:
        records: Raw records from fetch
        snapshot_id: Snapshot identifier (generated at refresh start)
        retrieved_at_utc: Actual retrieval timestamp from successful fetch
        query: Overpass query used

    Returns:
        Path to saved raw file
    """
    paths = get_snapshot_paths(snapshot_id)
    paths["raw_dir"].mkdir(parents=True, exist_ok=True)

    record_count = len(records)

    with paths["raw_file"].open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    metadata = generate_metadata(
        snapshot_id=snapshot_id,
        retrieved_at_utc=retrieved_at_utc,
        record_count=record_count,
        query=query,
        raw_file=paths["raw_file"].name,
        processed_file="cafes.csv",
        status=_SUCCESS_STATUS,
    )

    _write_metadata(paths["metadata_file"], metadata)

    return paths["raw_file"]


def save_processed_snapshot(
    df,
    snapshot_id: str,
    retrieved_at_utc: str,
    query: str,
) -> Path:
    """
    Save processed snapshot (CSV) and finalize metadata in both snapshot dirs.

    The snapshot is considered successful only once the processed artifact
    exists; both metadata files are updated with the finalized record count
    while preserving the actual retrieval timestamp.

    Args:
        df: Processed DataFrame
        snapshot_id: Snapshot identifier
        retrieved_at_utc: Actual retrieval timestamp from successful fetch
        query: Overpass query used

    Returns:
        Path to saved processed file
    """
    paths = get_snapshot_paths(snapshot_id)
    paths["processed_dir"].mkdir(parents=True, exist_ok=True)

    record_count = len(df)

    df.to_csv(paths["processed_file"], index=False, encoding="utf-8")

    metadata = generate_metadata(
        snapshot_id=snapshot_id,
        retrieved_at_utc=retrieved_at_utc,
        record_count=record_count,
        query=query,
        raw_file=paths["raw_file"].name,
        processed_file=paths["processed_file"].name,
        status=_SUCCESS_STATUS,
    )

    _write_metadata(paths["metadata_file"], metadata)
    _write_metadata(paths["processed_dir"] / "metadata.json", metadata)

    return paths["processed_file"]


def _is_readable(path: Path) -> bool:
    """Check whether a file exists and can be opened for reading."""
    if not path.exists():
        return False
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def load_snapshot_metadata(snapshot_id: str, require_manifest: bool = True) -> dict[str, Any] | None:
    """
    Load snapshot metadata, validating that the snapshot is complete.

    A snapshot is only considered valid if:
    1. status == "success"
    2. all required metadata keys exist
    3. both raw and processed artifacts exist and are readable
    4. final manifest.json exists and is readable (if require_manifest=True)
    5. manifest snapshot_id matches directory and metadata
    6. no quarantine.json exists

    Args:
        snapshot_id: Snapshot identifier
        require_manifest: Whether to require manifest.json for validity (default True for Phase 10)

    Returns:
        Metadata dictionary or None if not found/invalid/incomplete
    """
    paths = get_snapshot_paths(snapshot_id)

    if not _is_readable(paths["metadata_file"]):
        return None

    try:
        with paths["metadata_file"].open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    for key in REQUIRED_METADATA_KEYS:
        if key not in metadata:
            return None

    if metadata.get("status") != _SUCCESS_STATUS:
        return None

    if not _is_readable(paths["raw_file"]) or not _is_readable(paths["processed_file"]):
        return None

    if require_manifest:
        if not _is_readable(paths["manifest_file"]):
            return None

        try:
            with paths["manifest_file"].open("r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        if manifest_data.get("snapshot_id") != snapshot_id:
            return None
        if manifest_data.get("snapshot_id") != metadata.get("snapshot_id"):
            return None

    if paths["quarantine_file"].exists():
        return None

    return metadata


def list_snapshots() -> list[dict[str, Any]]:
    """
    List all successful snapshots, sorted newest first by snapshot ID.

    Returns:
        List of snapshot metadata dictionaries
    """
    if not SNAPSHOTS_RAW_DIR.exists():
        return []

    snapshots = []
    for snapshot_dir in SNAPSHOTS_RAW_DIR.iterdir():
        if snapshot_dir.is_dir():
            metadata = load_snapshot_metadata(snapshot_dir.name, require_manifest=True)
            if metadata:
                snapshots.append(metadata)

    snapshots.sort(key=lambda m: m["snapshot_id"], reverse=True)
    return snapshots


def get_latest_snapshot() -> str | None:
    """
    Get the snapshot ID of the most recent successful snapshot.

    Failed, incomplete, or missing snapshots are always ignored.

    Returns:
        Snapshot ID string or None if no valid snapshots exist
    """
    snapshots = list_snapshots()
    if not snapshots:
        return None
    return snapshots[0]["snapshot_id"]


def format_snapshot_list(snapshots: list[dict[str, Any]], verbose: bool = False) -> str:
    """
    Format snapshot list for CLI display.

    Args:
        snapshots: List of snapshot metadata
        verbose: Whether to show detailed metadata

    Returns:
        Formatted string
    """
    lines = []
    lines.append("Available Snapshots")
    lines.append("-------------------")

    if not snapshots:
        lines.append("(no successful snapshots found)")
        return "\n".join(lines)

    for meta in snapshots:
        lines.append(f"{meta['snapshot_id']}   {meta['record_count']} records")
        if verbose:
            lines.append(f"  Retrieved: {meta['retrieved_at_utc']}")
            lines.append(f"  Source: {meta['source']}")
            lines.append(f"  Method: {meta['retrieval_method']}")
            lines.append(f"  Status: {meta['status']}")

    return "\n".join(lines)


def main() -> None:
    """Command-line entry point for snapshot listing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Snapshot Management"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed snapshot metadata",
    )
    args = parser.parse_args()

    snapshots = list_snapshots()
    print(format_snapshot_list(snapshots, verbose=args.verbose))


if __name__ == "__main__":
    main()
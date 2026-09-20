"""Historical change analysis over Phase 8 snapshots.

Read-only analysis layer: discovers valid successful snapshots, builds
per-cafe observation history and field-level change history by comparing
adjacent snapshots, and exposes the results via CLI and CSV exports.

Source of truth is the existing snapshot files. Snapshots are never
modified. ``osm_id`` is the sole stable identity; names are display-only.

Counting semantics (documented, never mixed):
- unique entities: distinct ``osm_id`` values across analyzed snapshots
- observation counts: unique entities satisfying a presence condition
- change/field-change counts: snapshot-to-snapshot events
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from . import compare, snapshot, integrity, schema, quality
from .quality import is_missing

OBSERVATION_FIELDS = [
    "osm_id",
    "name",
    "first_observed_snapshot",
    "first_observed_at",
    "last_observed_snapshot",
    "last_observed_at",
    "snapshot_count",
]

CHANGE_FIELDS = [
    "osm_id",
    "snapshot_before",
    "snapshot_after",
    "changed_at",
    "field",
    "old_value",
    "new_value",
]

MISSING_EXPORT_VALUE = "missing"
MISSING_DISPLAY_VALUE = "(missing)"


class SnapshotDataError(Exception):
    """Raised when a snapshot's processed dataset cannot be loaded."""

    def __init__(self, snapshot_id: str, reason: str) -> None:
        super().__init__(f"Snapshot {snapshot_id}: {reason}")
        self.snapshot_id = snapshot_id
        self.reason = reason


def discover_snapshots() -> list[dict[str, Any]]:
    """
    Discover valid successful snapshots in chronological order.

    Reuses Phase 8 validity checks via ``snapshot.list_snapshots()``
    (failed, incomplete, missing-metadata, and unreadable snapshots are
    excluded there) and returns oldest-first.

    Returns:
        List of snapshot metadata dicts, oldest snapshot first
    """
    snapshots = snapshot.list_snapshots()
    snapshots.sort(key=lambda m: m["snapshot_id"])
    return snapshots


def load_snapshot_dataframe(snapshot_id: str) -> pd.DataFrame:
    """
    Load a snapshot's processed dataset.

    Args:
        snapshot_id: Snapshot identifier

    Returns:
        DataFrame with the snapshot's processed cafes, with string columns
        typed as str for schema compatibility

    Raises:
        SnapshotDataError: If the processed CSV cannot be read
    """
    paths = snapshot.get_snapshot_paths(snapshot_id)
    try:
        string_columns = {"osm_id", "name", "street", "housenumber", "city", "postcode", "cuisine", "opening_hours", "website", "phone", "source"}
        dtype_map = {col: str for col in string_columns}
        return pd.read_csv(paths["processed_file"], encoding="utf-8", dtype=dtype_map)
    except Exception as e:
        raise SnapshotDataError(snapshot_id, f"cannot read processed CSV: {e}") from e


def reconstruct_snapshot(snapshot_id: str) -> pd.DataFrame:
    """
    Reconstruct a snapshot's processed dataset with integrity gating.

    The snapshot must pass the full Phase 10 integrity contract before
    its processed CSV is loaded. Schema validation is re-checked after
    loading to ensure defense-in-depth.

    Args:
        snapshot_id: Snapshot identifier

    Returns:
        DataFrame with the snapshot's processed cafes, canonical 13 columns,
        sorted by osm_id ascending

    Raises:
        SnapshotDataError: If integrity verification fails or schema is invalid
    """
    report = integrity.verify_snapshot(snapshot_id)
    if report["status"] != "PASSED":
        raise SnapshotDataError(
            snapshot_id,
            f"integrity verification failed: {report['status']}",
        )
    df = load_snapshot_dataframe(snapshot_id)
    schema_result = schema.validate_schema(df)
    if not schema_result["valid"]:
        raise SnapshotDataError(
            snapshot_id,
            f"schema validation failed: {schema_result}",
        )
    df = df.sort_values("osm_id").reset_index(drop=True)
    return df


def _load_history_frames(
    snapshots: list[dict[str, Any]] | None,
) -> list[tuple[dict[str, Any], pd.DataFrame]]:
    """
    Load (metadata, DataFrame) pairs for analyzable snapshots.

    Snapshots whose processed CSV cannot be read are skipped with a
    stderr warning. Skipping a middle snapshot means its neighbors
    become adjacent for comparison purposes.

    Args:
        snapshots: Snapshot metadata list, or None to discover

    Returns:
        List of (metadata, DataFrame) tuples in chronological order
    """
    if snapshots is None:
        snapshots = discover_snapshots()

    frames = []
    for meta in snapshots:
        snapshot_id = meta["snapshot_id"]
        try:
            df = reconstruct_snapshot(snapshot_id)
        except SnapshotDataError as e:
            print(f"Warning: skipping snapshot: {e}", file=sys.stderr)
            continue
        frames.append((meta, df))
    return frames


def build_quality_history(snapshots=None):
    """
    Build historical data-quality evolution across valid snapshots.

    Each valid snapshot that passes the Phase 11.1 integrity gate
    produces one quality record. Invalid snapshots are skipped with
    a stderr warning, consistent with _load_history_frames.

    Args:
        snapshots: Snapshot metadata list oldest-first, or None to discover

    Returns:
        List of quality record dicts in chronological order, each containing:
        snapshot_id, retrieved_at_utc, record_count, valid_coordinate_records,
        invalid_coordinate_records, duplicate_osm_id_records,
        duplicate_location_name_records, field_completeness
    """
    frames = _load_history_frames(snapshots)

    quality_records = []
    for meta, df in frames:
        snapshot_id = meta["snapshot_id"]
        retrieved_at = meta["retrieved_at_utc"]
        total = len(df)

        if total == 0:
            field_completeness = {}
            for col in schema.CANONICAL_COLUMNS:
                field_completeness[col] = {"present": 0, "missing": 0, "completeness_percentage": 0.0}
            quality_records.append({
                "snapshot_id": snapshot_id,
                "retrieved_at_utc": retrieved_at,
                "record_count": 0,
                "valid_coordinate_records": 0,
                "invalid_coordinate_records": 0,
                "duplicate_osm_id_records": 0,
                "duplicate_location_name_records": 0,
                "field_completeness": field_completeness,
            })
            continue

        report = quality.generate_quality_report(df)

        field_completeness = dict(report["field_completeness"])
        for col in schema.CANONICAL_COLUMNS:
            if col not in field_completeness:
                missing = int(df[col].apply(is_missing).sum())
                present = total - missing
                pct = round((present / total) * 100, 1)
                field_completeness[col] = {
                    "present": present,
                    "missing": missing,
                    "completeness_percentage": pct,
                }

        quality_records.append({
            "snapshot_id": snapshot_id,
            "retrieved_at_utc": retrieved_at,
            "record_count": report["total_records"],
            "valid_coordinate_records": report["valid_coordinate_records"],
            "invalid_coordinate_records": report["invalid_coordinate_records"],
            "duplicate_osm_id_records": report["duplicate_osm_id_records"],
            "duplicate_location_name_records": report["duplicate_location_name_records"],
            "field_completeness": field_completeness,
        })
    return quality_records


def _plain_value(value: Any) -> Any:
    """
    Normalize a cell value for history records.

    Missing values become None; numpy floats become plain Python floats
    so records stay comparable and serializable. Other values pass through.
    """
    if is_missing(value):
        return None
    if isinstance(value, float):
        return float(value)
    return value


def _snapshot_rows(df: pd.DataFrame) -> dict[str, Any]:
    """
    Index a snapshot DataFrame by osm_id.

    Rows with a missing osm_id are ignored (they have no stable identity).
    Duplicate osm_id values within one snapshot resolve deterministically:
    the last row wins, consistent with ``compare.compare_datasets()``
    dict construction.
    """
    by_id: dict[str, Any] = {}
    for _, row in df.iterrows():
        value = row.get("osm_id")
        if is_missing(value):
            continue
        by_id[str(value).strip()] = row
    return by_id


def _display_name(value: Any) -> str:
    """Render a name for display, using the missing marker when absent."""
    if is_missing(value):
        return MISSING_DISPLAY_VALUE
    return str(value).strip()


def _latest_known_name(names_by_snapshot: list[tuple[str, Any]]) -> Any:
    """
    Return the latest-known non-missing name (display only, not identity).

    Args:
        names_by_snapshot: (snapshot_id, name) pairs oldest-first
    """
    for _, name in reversed(names_by_snapshot):
        if not is_missing(name):
            return name
    return None


def build_observation_history(
    snapshots: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build per-cafe observation history across snapshots.

    For each valid osm_id observed: first/last observed snapshot and
    retrieval timestamp (from snapshot metadata), and the number of
    successful snapshots containing it.

    A cafe absent from a later snapshot is "no longer observed" — this
    is a dataset observation, never proof of real-world closure. A cafe
    that disappears and reappears keeps a single history entry.

    Args:
        snapshots: Snapshot metadata list oldest-first, or None to discover

    Returns:
        Observation dicts sorted by osm_id ascending
    """
    frames = _load_history_frames(snapshots)

    first: dict[str, dict[str, Any]] = {}
    last: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    names: dict[str, list[tuple[str, Any]]] = {}

    for meta, df in frames:
        snapshot_id = meta["snapshot_id"]
        retrieved_at = meta["retrieved_at_utc"]
        for osm_id, row in _snapshot_rows(df).items():
            if osm_id not in first:
                first[osm_id] = {
                    "snapshot": snapshot_id,
                    "at": retrieved_at,
                }
            last[osm_id] = {"snapshot": snapshot_id, "at": retrieved_at}
            counts[osm_id] = counts.get(osm_id, 0) + 1
            names.setdefault(osm_id, []).append((snapshot_id, row.get("name")))

    observations = []
    for osm_id in sorted(first):
        observations.append({
            "osm_id": osm_id,
            "name": _latest_known_name(names[osm_id]),
            "first_observed_snapshot": first[osm_id]["snapshot"],
            "first_observed_at": first[osm_id]["at"],
            "last_observed_snapshot": last[osm_id]["snapshot"],
            "last_observed_at": last[osm_id]["at"],
            "snapshot_count": counts[osm_id],
        })
    return observations


def build_change_history(
    snapshots: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build field-level change history between adjacent snapshots.

    For snapshots A, B, C, D this compares A->B, B->C, C->D (never only
    A->D, so intermediate changes are preserved). Comparison reuses
    ``compare.compare_datasets()``, including its missing-value semantics:
    missing->populated and populated->missing count as changes, while
    equivalent missing representations (None/NaN/""/whitespace) do not.

    One record is created per changed field. ``changed_at`` is the
    retrieval timestamp of ``snapshot_after``.

    Args:
        snapshots: Snapshot metadata list oldest-first, or None to discover

    Returns:
        Change dicts sorted by (snapshot_after, osm_id, field)
    """
    frames = _load_history_frames(snapshots)

    changes = []
    for i in range(1, len(frames)):
        before_meta, before_df = frames[i - 1]
        after_meta, after_df = frames[i]
        result = compare.compare_datasets(before_df, after_df)
        for item in result["modified"]:
            for change in item["changes"]:
                changes.append({
                    "osm_id": item["osm_id"],
                    "snapshot_before": before_meta["snapshot_id"],
                    "snapshot_after": after_meta["snapshot_id"],
                    "changed_at": after_meta["retrieved_at_utc"],
                    "field": change["field"],
                    "old_value": _plain_value(change["old"]),
                    "new_value": _plain_value(change["new"]),
                })

    changes.sort(key=lambda c: (c["snapshot_after"], c["osm_id"], c["field"]))
    return changes


def summarize_history(
    snapshots: list[dict[str, Any]] | None = None,
    observations: list[dict[str, Any]] | None = None,
    changes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Summarize historical analysis with explicit counting semantics.

    Counts (all unique entities unless stated otherwise; categories may
    overlap — e.g. a cafe that appeared mid-history and later changed
    counts as both added and modified):
    - snapshots_analyzed: number of valid successful snapshots analyzed
    - unique_cafes: distinct osm_id values observed
    - added: entities first observed AFTER the earliest snapshot
    - no_longer_observed: entities last observed BEFORE the latest snapshot
    - modified: entities with at least one field-level change event
    - unchanged: entities present in EVERY analyzed snapshot with no changes
    - field_summary: field-level change EVENT counts (snapshot-to-snapshot
      events, not entities), ordered by count descending then field ascending

    Args:
        snapshots: Snapshot metadata list, or None to discover
        observations: Prebuilt observations, or None to build
        changes: Prebuilt changes, or None to build

    Returns:
        Summary dictionary
    """
    if snapshots is None:
        snapshots = discover_snapshots()
    if observations is None:
        observations = build_observation_history(snapshots)
    if changes is None:
        changes = build_change_history(snapshots)

    snapshot_ids = [m["snapshot_id"] for m in snapshots]
    earliest = snapshot_ids[0] if snapshot_ids else None
    latest = snapshot_ids[-1] if snapshot_ids else None

    changed_ids = {c["osm_id"] for c in changes}

    field_counts: dict[str, int] = {}
    for change in changes:
        field_counts[change["field"]] = field_counts.get(change["field"], 0) + 1
    field_summary = sorted(field_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    return {
        "snapshots_analyzed": len(snapshots),
        "snapshot_ids": snapshot_ids,
        "first_snapshot": earliest,
        "latest_snapshot": latest,
        "unique_cafes": len(observations),
        "added": sum(1 for o in observations if o["first_observed_snapshot"] != earliest),
        "no_longer_observed": sum(
            1 for o in observations if o["last_observed_snapshot"] != latest
        ),
        "modified": sum(1 for o in observations if o["osm_id"] in changed_ids),
        "unchanged": sum(
            1
            for o in observations
            if o["snapshot_count"] == len(snapshots) and o["osm_id"] not in changed_ids
        ),
        "field_summary": field_summary,
        "total_field_changes": len(changes),
    }


def format_summary(summary: dict[str, Any]) -> str:
    """
    Format the historical summary for CLI display.

    Args:
        summary: Summary dict from summarize_history

    Returns:
        Formatted string
    """
    lines = []
    lines.append("Historical Change Summary")
    lines.append("-------------------------")
    lines.append("")
    lines.append(f"Snapshots analyzed: {summary['snapshots_analyzed']}")
    lines.append("")
    lines.append(f"First snapshot: {summary['first_snapshot']}")
    lines.append(f"Latest snapshot: {summary['latest_snapshot']}")
    lines.append("")
    lines.append(f"Unique cafes observed: {summary['unique_cafes']}")
    lines.append("")
    lines.append(f"Added observations: {summary['added']}")
    lines.append(f"No-longer-observed observations: {summary['no_longer_observed']}")
    lines.append(f"Modified observations: {summary['modified']}")
    lines.append(f"Unchanged observations: {summary['unchanged']}")
    lines.append("")
    lines.append("(Counts are unique cafes; categories may overlap.)")
    return "\n".join(lines)


def format_fields(summary: dict[str, Any]) -> str:
    """
    Format the aggregate field-change summary for CLI display.

    Args:
        summary: Summary dict from summarize_history

    Returns:
        Formatted string
    """
    lines = []
    lines.append("Field Change Summary")
    lines.append("--------------------")
    if not summary["field_summary"]:
        lines.append("(no field changes observed)")
        return "\n".join(lines)
    width = max(len(field) for field, _ in summary["field_summary"])
    for field, count in summary["field_summary"]:
        lines.append(f"{field.ljust(width)}     {count}")
    return "\n".join(lines)


def format_cafe_history(
    osm_id: str,
    observations: list[dict[str, Any]],
    changes: list[dict[str, Any]],
) -> str:
    """
    Format the history of a single cafe for CLI display.

    Args:
        osm_id: Cafe identifier
        observations: Observation list from build_observation_history
        changes: Change list from build_change_history

    Returns:
        Formatted string
    """
    matches = [o for o in observations if o["osm_id"] == osm_id]
    observation = matches[0]
    cafe_changes = [c for c in changes if c["osm_id"] == osm_id]

    lines = []
    lines.append("Cafe History")
    lines.append("------------")
    lines.append("")
    lines.append(f"OSM ID: {osm_id}")
    lines.append(f"Name: {_display_name(observation['name'])}")
    lines.append("")
    lines.append(
        f"First observed: {observation['first_observed_snapshot']} "
        f"({observation['first_observed_at']})"
    )
    lines.append(
        f"Last observed: {observation['last_observed_snapshot']} "
        f"({observation['last_observed_at']})"
    )
    lines.append(f"Snapshots: {observation['snapshot_count']}")
    lines.append("")
    lines.append("Changes")
    lines.append("-------")
    if not cafe_changes:
        lines.append("(no field changes observed)")
        return "\n".join(lines)
    for change in cafe_changes:
        old = change["old_value"] if change["old_value"] is not None else MISSING_DISPLAY_VALUE
        new = change["new_value"] if change["new_value"] is not None else MISSING_DISPLAY_VALUE
        lines.append("")
        lines.append(f"{change['changed_at']}")
        lines.append(f"  {change['field']}")
        lines.append(f"    Old: {old}")
        lines.append(f"    New: {new}")
    return "\n".join(lines)


def export_observations_csv(
    observations: list[dict[str, Any]], output_path: Path
) -> Path:
    """
    Export observation history to CSV.

    Args:
        observations: Observation list from build_observation_history
        output_path: Destination CSV path (parents created as needed)

    Returns:
        The output path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for observation in observations:
            writer.writerow({field: observation.get(field) for field in OBSERVATION_FIELDS})
    return output_path


def export_changes_csv(changes: list[dict[str, Any]], output_path: Path) -> Path:
    """
    Export field-level change history to CSV with deterministic row order.

    Missing values are serialized as the literal string "missing"
    (never arbitrary Pandas NaN formatting).

    Args:
        changes: Change list from build_change_history
        output_path: Destination CSV path (parents created as needed)

    Returns:
        The output path
    """
    ordered = sorted(changes, key=lambda c: (c["snapshot_after"], c["osm_id"], c["field"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHANGE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for change in ordered:
            row = {field: change.get(field) for field in CHANGE_FIELDS}
            if row["old_value"] is None:
                row["old_value"] = MISSING_EXPORT_VALUE
            if row["new_value"] is None:
                row["new_value"] = MISSING_EXPORT_VALUE
            writer.writerow(row)
    return output_path


def format_reconstruction(df: pd.DataFrame, snapshot_id: str, retrieved_at: str) -> str:
    """Format a reconstructed snapshot for CLI display."""
    lines = []
    lines.append(f"Snapshot: {snapshot_id}")
    lines.append(f"Retrieved at: {retrieved_at}")
    lines.append(f"Records: {len(df)}")
    lines.append(f"Columns: {', '.join(df.columns.tolist())}")
    lines.append("")
    lines.append("Records (sorted by osm_id):")
    for _, row in df.iterrows():
        osm_id = row.get("osm_id", "")
        name = row.get("name", "")
        lines.append(f"  {osm_id}: {name}")
    return "\n".join(lines)


def export_reconstruction_csv(df: pd.DataFrame, output_path: Path) -> Path:
    """Export a reconstructed DataFrame to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def format_quality_history(records: list[dict[str, Any]]) -> str:
    """Format historical quality evolution for CLI display."""
    lines = []
    if not records:
        lines.append("No valid snapshots available.")
        return "\n".join(lines)
    for record in records:
        lines.append(f"Snapshot: {record['snapshot_id']}")
        lines.append(f"Retrieved at: {record['retrieved_at_utc']}")
        lines.append(f"Records: {record['record_count']}")
        lines.append(f"Valid coordinates: {record['valid_coordinate_records']}")
        lines.append(f"Invalid coordinates: {record['invalid_coordinate_records']}")
        lines.append(f"Duplicate OSM IDs: {record['duplicate_osm_id_records']}")
        lines.append(f"Duplicate location names: {record['duplicate_location_name_records']}")
        lines.append("Field completeness:")
        for field in sorted(record["field_completeness"].keys()):
            fc = record["field_completeness"][field]
            lines.append(f"  {field}: {fc['completeness_percentage']}% "
                         f"(present={fc['present']}, missing={fc['missing']})")
        lines.append("")
    return "\n".join(lines)


def export_quality_csv(records: list[dict[str, Any]], output_path: Path) -> Path:
    """Export quality history to flat CSV with one row per snapshot per field."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_id", "retrieved_at_utc", "field",
                          "present", "missing", "completeness_percentage"])
        for record in records:
            for field, fc in record["field_completeness"].items():
                writer.writerow([
                    record["snapshot_id"],
                    record["retrieved_at_utc"],
                    field,
                    fc["present"],
                    fc["missing"],
                    fc["completeness_percentage"],
                ])
    return output_path


def main() -> None:
    """Command-line entry point for historical change analysis."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Historical Change Analysis"
    )
    parser.add_argument(
        "--osm-id",
        default=None,
        help="Show history for a single cafe by OSM ID",
    )
    parser.add_argument(
        "--fields",
        action="store_true",
        help="Show aggregate field-level change summary",
    )
    parser.add_argument(
        "--reconstruct",
        action="store_true",
        help="Reconstruct a snapshot by ID",
    )
    parser.add_argument(
        "--snapshot-id",
        default=None,
        help="Snapshot ID for reconstruction",
    )
    parser.add_argument(
        "--quality",
        action="store_true",
        help="Show historical data-quality evolution",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Export observation history or reconstruction to CSV at PATH",
    )
    parser.add_argument(
        "--changes-output",
        default=None,
        help="Export field-level change history to CSV at PATH",
    )
    parser.add_argument(
        "--quality-output",
        default=None,
        help="Export quality history to CSV at PATH",
    )
    args = parser.parse_args()

    if args.reconstruct:
        if not args.snapshot_id:
            print("Error: --snapshot-id is required for --reconstruct", file=sys.stderr)
            sys.exit(1)
        try:
            df = reconstruct_snapshot(args.snapshot_id)
        except SnapshotDataError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        meta = snapshot.load_snapshot_metadata(args.snapshot_id, require_manifest=True)
        retrieved_at = meta["retrieved_at_utc"] if meta else ""
        if args.json:
            result = {
                "snapshot_id": args.snapshot_id,
                "retrieved_at_utc": retrieved_at,
                "record_count": len(df),
                "columns": df.columns.tolist(),
                "records": df.to_dict(orient="records"),
            }
            print(json.dumps(result, indent=2, default=str))
        elif args.output:
            export_reconstruction_csv(df, Path(args.output))
            print(f"Reconstruction exported to {args.output}")
        else:
            print(format_reconstruction(df, args.snapshot_id, retrieved_at))
        return

    if args.quality:
        records = build_quality_history()
        if args.json:
            print(json.dumps(records, indent=2, default=str))
        elif args.quality_output:
            export_quality_csv(records, Path(args.quality_output))
            print(f"Quality history exported to {args.quality_output}")
        else:
            print(format_quality_history(records))
        return

    snapshots = discover_snapshots()
    observations = build_observation_history(snapshots)
    changes = build_change_history(snapshots)

    if args.osm_id:
        if not any(o["osm_id"] == args.osm_id for o in observations):
            print(
                f"Error: OSM ID not found in any valid snapshot: {args.osm_id}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(format_cafe_history(args.osm_id, observations, changes))
        return

    summary = summarize_history(snapshots, observations, changes)
    if args.fields:
        print(format_fields(summary))
    else:
        print(format_summary(summary))

    if args.output:
        export_observations_csv(observations, Path(args.output))
        print(f"Observation history exported to {args.output}")

    if args.changes_output:
        export_changes_csv(changes, Path(args.changes_output))
        print(f"Change history exported to {args.changes_output}")


if __name__ == "__main__":
    main()
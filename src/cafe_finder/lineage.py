"""Historical-analysis lineage for Lucknow Cafe Finder.

Connects OpenStreetMap -> Overpass API -> Snapshot -> Processed dataset ->
Adjacent comparisons -> Historical analysis by reading lineage information
from existing Phase 8 snapshot metadata. No snapshot-generation logic is
duplicated here.

``retrieved_at_utc`` = when source data was retrieved (from metadata).
``generated_at_utc`` = when this lineage report was generated (now).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .history import discover_snapshots

ANALYSIS_TYPE = "historical_change_analysis"


class LineageError(Exception):
    """Raised when lineage cannot be established from snapshot metadata."""


def _snapshot_lineage(meta: dict[str, Any]) -> dict[str, Any]:
    """
    Extract lineage details for one snapshot from its metadata.

    Args:
        meta: Snapshot metadata dict from Phase 8 discovery

    Returns:
        Lineage dict for the snapshot

    Raises:
        LineageError: If required metadata is missing
    """
    try:
        return {
            "snapshot_id": meta["snapshot_id"],
            "retrieved_at_utc": meta["retrieved_at_utc"],
            "record_count": meta["record_count"],
            "raw_file": meta["raw_file"],
            "processed_file": meta["processed_file"],
        }
    except KeyError as e:
        raise LineageError(
            f"Snapshot metadata is missing required key: {e} "
            f"(snapshot: {meta.get('snapshot_id', 'unknown')})"
        ) from e


def generate_lineage(
    snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Generate the historical-analysis lineage report.

    Source, retrieval method, snapshot IDs, retrieval timestamps, record
    counts, and artifact references all come from actual Phase 8 snapshot
    metadata. Nothing is fabricated.

    Args:
        snapshots: Snapshot metadata list oldest-first, or None to discover

    Returns:
        Lineage report dictionary

    Raises:
        LineageError: If no valid successful snapshots exist
    """
    if snapshots is None:
        snapshots = discover_snapshots()

    if not snapshots:
        raise LineageError(
            "No valid successful snapshots found; "
            "cannot establish historical-analysis lineage."
        )

    per_snapshot = [_snapshot_lineage(meta) for meta in snapshots]
    first = per_snapshot[0]
    latest = per_snapshot[-1]

    return {
        "analysis_type": ANALYSIS_TYPE,
        "source": snapshots[0]["source"],
        "retrieval_method": snapshots[0]["retrieval_method"],
        "snapshots_analyzed": len(snapshots),
        "snapshot_ids": [meta["snapshot_id"] for meta in snapshots],
        "first_snapshot": dict(first),
        "latest_snapshot": dict(latest),
        "snapshots": per_snapshot,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def format_lineage(report: dict[str, Any]) -> str:
    """
    Format the lineage report for CLI display.

    Args:
        report: Lineage dict from generate_lineage

    Returns:
        Formatted string
    """
    first = report["first_snapshot"]
    latest = report["latest_snapshot"]

    lines = []
    lines.append("Historical Analysis Lineage")
    lines.append("---------------------------")
    lines.append("")
    lines.append(f"Source: {report['source']}")
    lines.append(f"Retrieval method: {report['retrieval_method']}")
    lines.append("")
    lines.append(f"Snapshots analyzed: {report['snapshots_analyzed']}")
    lines.append("")
    lines.append("First snapshot:")
    lines.append(f"  ID: {first['snapshot_id']}")
    lines.append(f"  Retrieved: {first['retrieved_at_utc']}")
    lines.append(f"  Records: {first['record_count']}")
    lines.append("")
    lines.append("Latest snapshot:")
    lines.append(f"  ID: {latest['snapshot_id']}")
    lines.append(f"  Retrieved: {latest['retrieved_at_utc']}")
    lines.append(f"  Records: {latest['record_count']}")
    lines.append("")
    lines.append("Analysis generated:")
    lines.append(f"  {report['generated_at_utc']}")
    return "\n".join(lines)


def export_lineage_json(report: dict[str, Any], output_path: Path) -> Path:
    """
    Export the lineage report as JSON.

    Args:
        report: Lineage dict from generate_lineage
        output_path: Destination JSON path (parents created as needed)

    Returns:
        The output path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return output_path


def main() -> None:
    """Command-line entry point for historical-analysis lineage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Historical Analysis Lineage"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Export lineage report as JSON to PATH",
    )
    args = parser.parse_args()

    try:
        report = generate_lineage()
    except LineageError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(format_lineage(report))

    if args.output:
        export_lineage_json(report, Path(args.output))
        print(f"Lineage exported to {args.output}")


if __name__ == "__main__":
    main()
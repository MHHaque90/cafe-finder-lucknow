"""Dataset comparison for detecting changes between snapshots."""

import sys
from pathlib import Path

import pandas as pd

from .quality import is_missing

TRACKED_FIELDS = [
    "osm_id",
    "name",
    "latitude",
    "longitude",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
    "source",
]


def fields_equal(val1, val2) -> bool:
    """
    Compare two field values using consistent missing-value semantics.

    Two values are considered equal if:
    - Both are missing (via quality.is_missing)
    - Both are non-missing and numerically equal (for numbers)
    - Both are non-missing and equal as strings (whitespace-insensitive)

    Args:
        val1: First value
        val2: Second value

    Returns:
        True if values are considered equal
    """
    val1_missing = is_missing(val1)
    val2_missing = is_missing(val2)

    if val1_missing and val2_missing:
        return True
    if val1_missing or val2_missing:
        return False

    if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
        return val1 == val2

    return str(val1).strip() == str(val2).strip()


def _extract_osm_id(row) -> str:
    """
    Extract a stable osm_id string from a record row.

    Missing values (NaN, None, blank) yield an empty string so they are
    never treated as a real identity.

    Args:
        row: DataFrame row or record dict

    Returns:
        Trimmed osm_id string or empty string if missing
    """
    value = row.get("osm_id")
    if is_missing(value):
        return ""
    return str(value).strip()


def compare_datasets(old_df: pd.DataFrame, new_df: pd.DataFrame) -> dict:
    """
    Compare two datasets using osm_id as the stable identity.

    Args:
        old_df: Previous dataset
        new_df: New dataset

    Returns:
        Dictionary with added, removed, modified, unchanged, field_changes
    """
    old_by_id: dict[str, pd.Series] = {}
    for _, row in old_df.iterrows():
        osm_id = _extract_osm_id(row)
        if osm_id:
            old_by_id[osm_id] = row

    new_by_id: dict[str, pd.Series] = {}
    for _, row in new_df.iterrows():
        osm_id = _extract_osm_id(row)
        if osm_id:
            new_by_id[osm_id] = row

    old_ids = set(old_by_id)
    new_ids = set(new_by_id)

    added = [new_by_id[i] for i in sorted(new_ids - old_ids)]
    removed = [old_by_id[i] for i in sorted(old_ids - new_ids)]

    modified = []
    unchanged = []
    field_changes = []

    for osm_id_str in sorted(old_ids & new_ids):
        old_row = old_by_id[osm_id_str]
        new_row = new_by_id[osm_id_str]
        changes = []
        for field in TRACKED_FIELDS:
            old_val = old_row.get(field)
            new_val = new_row.get(field)
            if not fields_equal(old_val, new_val):
                changes.append({
                    "field": field,
                    "old": old_val if not is_missing(old_val) else None,
                    "new": new_val if not is_missing(new_val) else None,
                })
        if changes:
            modified.append({
                "osm_id": osm_id_str,
                "name": new_row.get("name", ""),
                "changes": changes,
            })
            field_changes.extend(changes)
        else:
            unchanged.append({
                "osm_id": osm_id_str,
                "name": new_row.get("name", ""),
            })

    return {
        "old_record_count": len(old_df),
        "new_record_count": len(new_df),
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "field_changes": field_changes,
    }


def format_comparison(result: dict) -> str:
    """
    Format comparison result for CLI display.

    Args:
        result: Comparison result from compare_datasets

    Returns:
        Formatted string
    """
    lines = []
    lines.append("Dataset Comparison")
    lines.append("------------------")
    lines.append(f"Previous records: {result['old_record_count']}")
    lines.append(f"Current records:  {result['new_record_count']}")
    lines.append("")

    added = len(result["added"])
    removed = len(result["removed"])
    modified = len(result["modified"])
    unchanged = len(result["unchanged"])

    lines.append(f"Added:      {added}")
    lines.append(f"Removed:    {removed}")
    lines.append(f"Modified:   {modified}")
    lines.append(f"Unchanged:  {unchanged}")

    return "\n".join(lines)


def _display_name(row) -> str:
    """Return a display name for a record, or empty string if missing."""
    name = row.get("name", "")
    if is_missing(name):
        return ""
    return str(name).strip()


def format_verbose_comparison(result: dict) -> str:
    """
    Format comparison result with detailed field changes.

    Args:
        result: Comparison result from compare_datasets

    Returns:
        Formatted string with per-record details
    """
    lines = []
    lines.append("Dataset Comparison")
    lines.append("------------------")
    lines.append(f"Previous records: {result['old_record_count']}")
    lines.append(f"Current records:  {result['new_record_count']}")
    lines.append("")

    added = len(result["added"])
    removed = len(result["removed"])
    modified = len(result["modified"])
    unchanged = len(result["unchanged"])

    lines.append(f"Added:      {added}")
    lines.append(f"Removed:    {removed}")
    lines.append(f"Modified:   {modified}")
    lines.append(f"Unchanged:  {unchanged}")
    lines.append("")

    if result["added"]:
        lines.append("Added Records")
        lines.append("-------------")
        for row in result["added"]:
            osm_id = row.get("osm_id", "")
            name = _display_name(row)
            lines.append(f"  + {osm_id}: {name}" if name else f"  + {osm_id}")
        lines.append("")

    if result["removed"]:
        lines.append("Removed Records")
        lines.append("---------------")
        for row in result["removed"]:
            osm_id = row.get("osm_id", "")
            name = _display_name(row)
            lines.append(f"  - {osm_id}: {name}" if name else f"  - {osm_id}")
        lines.append("")

    if result["modified"]:
        lines.append("Modified Records")
        lines.append("----------------")
        for item in result["modified"]:
            osm_id = item["osm_id"]
            name = item["name"]
            lines.append(f"  ~ {osm_id}: {name}" if name else f"  ~ {osm_id}")
            for change in item["changes"]:
                field = change["field"]
                old = change["old"] if change["old"] is not None else "(missing)"
                new = change["new"] if change["new"] is not None else "(missing)"
                lines.append(f"      {field}: {old} -> {new}")
        lines.append("")

    if result["unchanged"]:
        lines.append("Unchanged Records")
        lines.append("-----------------")
        for item in result["unchanged"]:
            lines.append(f"  = {item['osm_id']}: {item['name']}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Command-line entry point for dataset comparison."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Dataset Comparison"
    )
    parser.add_argument("old_csv", help="Path to previous dataset CSV")
    parser.add_argument("new_csv", help="Path to new dataset CSV")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed comparison output",
    )
    args = parser.parse_args()

    old_path = Path(args.old_csv)
    new_path = Path(args.new_csv)

    if not old_path.exists():
        print(f"Error: Old CSV not found: {old_path}", file=sys.stderr)
        sys.exit(1)

    if not new_path.exists():
        print(f"Error: New CSV not found: {new_path}", file=sys.stderr)
        sys.exit(1)

    try:
        old_df = pd.read_csv(old_path, encoding="utf-8")
        new_df = pd.read_csv(new_path, encoding="utf-8")
    except Exception as e:
        print(f"Error reading CSV files: {e}", file=sys.stderr)
        sys.exit(1)

    result = compare_datasets(old_df, new_df)

    if args.verbose:
        print(format_verbose_comparison(result))
    else:
        print(format_comparison(result))


if __name__ == "__main__":
    main()
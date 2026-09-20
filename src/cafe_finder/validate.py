"""Validation checks for cleaned cafe records."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating a single record."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


def validate_record(record: dict[str, Any]) -> ValidationResult:
    """
    Validate a single cleaned cafe record.

    Checks:
    - Required identifier (osm_id) exists
    - Latitude exists and is in valid range [-90, 90]
    - Longitude exists and is in valid range [-180, 180]
    - Name exists (warning only, not required)
    - Not (0, 0) coordinates

    Args:
        record: Cleaned cafe record dict

    Returns:
        ValidationResult with validity status and messages
    """
    errors: list[str] = []
    warnings: list[str] = []

    osm_id = record.get("osm_id")
    if not osm_id:
        errors.append("Missing required field: osm_id")

    lat = record.get("latitude")
    lon = record.get("longitude")

    if lat is None:
        errors.append("Missing required field: latitude")
    elif not (-90 <= lat <= 90):
        errors.append(f"Invalid latitude: {lat} (must be between -90 and 90)")

    if lon is None:
        errors.append("Missing required field: longitude")
    elif not (-180 <= lon <= 180):
        errors.append(f"Invalid longitude: {lon} (must be between -180 and 180)")

    if lat == 0 and lon == 0:
        errors.append("Coordinates are (0, 0) - likely placeholder")

    name = record.get("name")
    if name is None or name == "":
        warnings.append("Missing cafe name")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_duplicates(records: list[dict[str, Any]]) -> list[str]:
    """
    Check for duplicate OSM IDs in the dataset.

    Args:
        records: List of records to check

    Returns:
        List of duplicate OSM IDs found
    """
    seen: dict[str, int] = {}
    duplicates: list[str] = []

    for record in records:
        osm_id = record.get("osm_id")
        if osm_id:
            if osm_id in seen:
                if seen[osm_id] == 1:
                    duplicates.append(osm_id)
                seen[osm_id] += 1
            else:
                seen[osm_id] = 1

    return duplicates


def validate_dataset(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Validate entire dataset and return summary statistics.

    Args:
        records: List of cleaned records

    Returns:
        Dict with validation summary
    """
    if not records:
        return {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "records_with_warnings": 0,
            "duplicate_osm_ids": [],
            "is_empty": True,
            "errors_by_type": {},
        }

    duplicate_ids = validate_duplicates(records)

    valid_count = 0
    invalid_count = 0
    warnings_count = 0
    errors_by_type: dict[str, int] = {}

    for record in records:
        result = validate_record(record)
        if result.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            for error in result.errors:
                errors_by_type[error] = errors_by_type.get(error, 0) + 1
        if result.warnings:
            warnings_count += 1

    return {
        "total_records": len(records),
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "records_with_warnings": warnings_count,
        "duplicate_osm_ids": duplicate_ids,
        "is_empty": False,
        "errors_by_type": errors_by_type,
    }


def filter_valid_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter records to keep only valid ones.

    Args:
        records: List of records to filter

    Returns:
        List of valid records only
    """
    return [r for r in records if validate_record(r).is_valid]


def main() -> None:
    """Command-line entry point for validation."""
    import json
    import sys

    from cafe_finder.config import RAW_DIR

    input_path = RAW_DIR / "lucknow_cafes_cleaned.json"

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    summary = validate_dataset(records)

    print("=== Validation Summary ===")
    print(f"Total records: {summary['total_records']}")
    print(f"Valid records: {summary['valid_records']}")
    print(f"Invalid records: {summary['invalid_records']}")
    print(f"Records with warnings: {summary['records_with_warnings']}")
    print(f"Duplicate OSM IDs: {len(summary['duplicate_osm_ids'])}")
    if summary["duplicate_osm_ids"]:
        for dup in summary["duplicate_osm_ids"]:
            print(f"  - {dup}")
    if summary["errors_by_type"]:
        print("Errors by type:")
        for error, count in sorted(summary["errors_by_type"].items(), key=lambda x: -x[1]):
            print(f"  {count}x: {error}")

    if summary["is_empty"]:
        print("\nWARNING: Dataset is empty!")
        sys.exit(1)

    if summary["invalid_records"] > 0:
        print(f"\nWARNING: {summary['invalid_records']} invalid records found")
        sys.exit(1)

    print("\nAll records valid!")
    sys.exit(0)


if __name__ == "__main__":
    main()
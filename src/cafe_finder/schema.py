"""Data schema definition and validation for Lucknow Cafe Finder."""

from typing import Any

import pandas as pd

from .quality import is_missing

SCHEMA_VERSION = 1

CANONICAL_COLUMNS = [
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

REQUIRED_COLUMNS = CANONICAL_COLUMNS.copy()

STRING_FIELDS = {
    "name",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
    "source",
    "osm_id",
}

NUMERIC_FIELDS = {"latitude", "longitude"}

# Only osm_id and name are strictly required non-nullable; other string fields are commonly missing in OSM data
NULLABLE_STRING_FIELDS = {
    "source",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
}


def get_schema_version() -> int:
    """Return the current schema version."""
    return SCHEMA_VERSION


def get_canonical_columns() -> list[str]:
    """Return the canonical column order."""
    return CANONICAL_COLUMNS.copy()


def get_required_columns() -> list[str]:
    """Return the required columns."""
    return REQUIRED_COLUMNS.copy()


def _validate_osm_id(value: Any, col_errors: dict[str, list[str]]) -> None:
    """Validate osm_id field for a single row."""
    if is_missing(value):
        col_errors["osm_id"].append("osm_id: missing")
        return
    if not isinstance(value, str):
        col_errors["osm_id"].append("osm_id: must be string")
        return
    if value.strip() == "":
        col_errors["osm_id"].append("osm_id: empty or whitespace-only")


def _validate_source(value: Any, col_errors: dict[str, list[str]]) -> None:
    """Validate source field for a single row."""
    if is_missing(value):
        return
    if not isinstance(value, str):
        col_errors["source"].append("source: must be string")


def _validate_string_field(field: str, value: Any, col_errors: dict[str, list[str]]) -> None:
    """Validate a string field for a single row."""
    if is_missing(value):
        return
    if not isinstance(value, str):
        col_errors[field].append(f"{field}: must be string")


def _validate_numeric_field(field: str, value: Any, col_errors: dict[str, list[str]]) -> None:
    """Validate a numeric field for a single row."""
    if is_missing(value):
        return
    try:
        float(value)
    except (TypeError, ValueError):
        col_errors[field].append(f"{field}: must be numeric")


def validate_schema(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validate DataFrame against the canonical schema.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "schema_version": int,
            "missing_columns": list[str],
            "unexpected_columns": list[str],
            "invalid_types": dict[str, str],
            "column_order_valid": bool
        }
    """
    result = {
        "valid": True,
        "schema_version": SCHEMA_VERSION,
        "missing_columns": [],
        "unexpected_columns": [],
        "invalid_types": {},
        "column_order_valid": True,
    }

    df_columns = list(df.columns)

    for col in CANONICAL_COLUMNS:
        if col not in df_columns:
            result["missing_columns"].append(col)

    for col in df_columns:
        if col not in CANONICAL_COLUMNS:
            result["unexpected_columns"].append(col)

    result["column_order_valid"] = df_columns == CANONICAL_COLUMNS

    row_errors: dict[int, list[str]] = {}

    # Fields that must not be missing (required and non-nullable)
    REQUIRED_NON_NULLABLE = (set(REQUIRED_COLUMNS) - NULLABLE_STRING_FIELDS) | NUMERIC_FIELDS

    # Collect errors by column to ensure deterministic ordering
    col_errors: dict[str, list[str]] = {col: [] for col in CANONICAL_COLUMNS}

    for idx, row in df.iterrows():
        if "osm_id" in df.columns:
            _validate_osm_id(row["osm_id"], col_errors)
        else:
            col_errors["osm_id"].append("osm_id: column missing")

        if "source" in df.columns:
            _validate_source(row["source"], col_errors)

        for field in STRING_FIELDS - {"osm_id", "source"}:
            if field in df.columns:
                _validate_string_field(field, row[field], col_errors)

        for field in NUMERIC_FIELDS:
            if field in df.columns:
                _validate_numeric_field(field, row[field], col_errors)

        # Check for missing values in required non-nullable fields
        for field in REQUIRED_NON_NULLABLE:
            if field in df.columns and is_missing(row[field]):
                col_errors[field].append(f"{field}: missing")

    if any(col_errors.values()):
        result["valid"] = False
        for col in CANONICAL_COLUMNS:
            if col_errors[col]:
                result["invalid_types"][col] = col_errors[col][0]

    if result["missing_columns"] or result["unexpected_columns"] or not result["column_order_valid"]:
        result["valid"] = False

    return result


def main() -> None:
    """Command-line entry point for schema validation."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Schema Validation"
    )
    parser.add_argument(
        "csv_path",
        help="Path to CSV file to validate",
    )
    args = parser.parse_args()

    from pathlib import Path
    csv_path = Path(args.csv_path)

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    result = validate_schema(df)

    if result["valid"]:
        print("Schema validation: PASSED")
        sys.exit(0)
    else:
        print("Schema validation: FAILED", file=sys.stderr)
        print(f"  Missing columns: {result['missing_columns']}", file=sys.stderr)
        print(f"  Unexpected columns: {result['unexpected_columns']}", file=sys.stderr)
        print(f"  Column order valid: {result['column_order_valid']}", file=sys.stderr)
        if result["invalid_types"]:
            print("  Type errors:", file=sys.stderr)
            for col, error in result["invalid_types"].items():
                print(f"    {col}: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
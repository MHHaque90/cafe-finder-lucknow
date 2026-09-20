"""Data quality and provenance for Lucknow Cafe Finder dataset."""

import argparse
import sys
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from cafe_finder.config import DEFAULT_CSV_PATH

IMPORTANT_FIELDS = [
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
]

SOURCE = "OpenStreetMap"
RETRIEVAL_METHOD = "Overpass API"


def is_missing(value: Any) -> bool:
    """
    Check if a value is considered missing.

    Missing values are:
    - None
    - NaN / NaT / pd.NA
    - Empty string
    - Whitespace-only string

    Args:
        value: Value to check

    Returns:
        True if value is missing, False otherwise
    """
    if value is None:
        return True

    if isinstance(value, float) and pd.isna(value):
        return True

    if isinstance(value, (pd.Timestamp, pd.Timedelta)) and pd.isna(value):
        return True

    if hasattr(pd, "isna") and pd.isna(value):
        return True

    if isinstance(value, str):
        return value.strip() == ""

    return False


def _is_missing_series(series: pd.Series) -> pd.Series:
    """Vectorized missing check for a Series."""
    return series.apply(is_missing)


def calculate_completeness(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """
    Calculate completeness metrics for each important field.

    Args:
        df: DataFrame with cafe data

    Returns:
        Dictionary mapping field name to dict with present_count,
        missing_count, and completeness_percentage
    """
    total = len(df)
    result = {}

    for field in IMPORTANT_FIELDS:
        if field not in df.columns:
            result[field] = {
                "present_count": 0,
                "missing_count": total,
                "completeness_percentage": 0.0,
            }
            continue

        missing_mask = _is_missing_series(df[field])
        missing_count = int(missing_mask.sum())
        present_count = total - missing_count
        pct = round((present_count / total) * 100, 1) if total > 0 else 0.0

        result[field] = {
            "present_count": present_count,
            "missing_count": missing_count,
            "completeness_percentage": pct,
        }

    return result


def validate_coordinates(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validate latitude and longitude coordinates.

    Args:
        df: DataFrame with cafe data

    Returns:
        Dictionary with validation results including invalid records detail
    """
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return {
            "valid_count": 0,
            "invalid_count": len(df),
            "invalid_records": [
                {"index": i, "osm_id": row.get("osm_id"), "latitude": None, "longitude": None, "issues": ["missing_coordinate_columns"]}
                for i, row in df.iterrows()
            ],
        }

    lat_series = pd.to_numeric(df["latitude"], errors="coerce")
    lon_series = pd.to_numeric(df["longitude"], errors="coerce")

    invalid_records = []
    valid_count = 0

    for idx in df.index:
        issues = []
        lat_raw = df.at[idx, "latitude"]
        lon_raw = df.at[idx, "longitude"]
        lat = lat_series.at[idx]
        lon = lon_series.at[idx]
        osm_id = df.at[idx, "osm_id"] if "osm_id" in df.columns else None

        # Check latitude
        if is_missing(lat_raw):
            issues.append("missing_latitude")
        elif isinstance(lat_raw, str):
            try:
                float(lat_raw)
            except (ValueError, TypeError):
                issues.append("non_numeric_latitude")
        elif pd.isna(lat):
            issues.append("missing_latitude")
        elif not (-90 <= lat <= 90):
            issues.append("latitude_out_of_range")

        # Check longitude
        if is_missing(lon_raw):
            issues.append("missing_longitude")
        elif isinstance(lon_raw, str):
            try:
                float(lon_raw)
            except (ValueError, TypeError):
                issues.append("non_numeric_longitude")
        elif pd.isna(lon):
            issues.append("missing_longitude")
        elif not (-180 <= lon <= 180):
            issues.append("longitude_out_of_range")

        if issues:
            invalid_records.append({
                "index": idx,
                "osm_id": osm_id,
                "latitude": lat_raw,
                "longitude": lon_raw,
                "issues": issues,
            })
        else:
            valid_count += 1

    return {
        "valid_count": valid_count,
        "invalid_count": len(invalid_records),
        "invalid_records": invalid_records,
    }


def _normalize_name(name: Any) -> str:
    """Normalize name for duplicate detection: trim, collapse whitespace, casefold."""
    if is_missing(name):
        return ""
    normalized = " ".join(str(name).split())
    return normalized.casefold()


def _normalize_coord(coord: Any) -> float | None:
    """Convert coordinate to numeric and round to 6 decimal places."""
    try:
        return round(float(coord), 6)
    except (TypeError, ValueError):
        return None


def detect_duplicates(df: pd.DataFrame) -> dict[str, Any]:
    """
    Detect duplicate records by OSM ID and by coordinate+name combination.

    Args:
        df: DataFrame with cafe data

    Returns:
        Dictionary with duplicate detection results
    """
    # OSM ID duplicates
    duplicate_osm_id_records = 0
    duplicate_osm_id_values = []
    if "osm_id" in df.columns:
        osm_ids = df["osm_id"]
        valid_mask = osm_ids.notna() & (osm_ids != "")
        valid_osm_ids = osm_ids[valid_mask]
        duplicated_mask = valid_osm_ids.duplicated(keep=False)
        duplicate_osm_id_records = int(duplicated_mask.sum())
        duplicate_osm_id_values = sorted(valid_osm_ids[duplicated_mask].unique().tolist())

    # Coordinate + name duplicates
    duplicate_location_name_records = 0
    duplicate_location_name_groups = []

    if all(c in df.columns for c in ["latitude", "longitude", "name"]):
        lat_norm = df["latitude"].apply(_normalize_coord)
        lon_norm = df["longitude"].apply(_normalize_coord)
        name_norm = df["name"].apply(_normalize_name)

        valid_mask = lat_norm.notna() & lon_norm.notna()
        keys = list(zip(lat_norm[valid_mask], lon_norm[valid_mask], name_norm[valid_mask], strict=False))

        if keys:
            key_series = pd.Series(keys, index=valid_mask[valid_mask].index)
            duplicated_mask = key_series.duplicated(keep=False)
            duplicate_location_name_records = int(duplicated_mask.sum())

            if duplicate_location_name_records > 0:
                dup_keys = key_series[duplicated_mask]
                for key in dup_keys.unique():
                    indices = dup_keys[dup_keys == key].index.tolist()
                    duplicate_location_name_groups.append({
                        "key": {"latitude": key[0], "longitude": key[1], "name": key[2]},
                        "indices": indices,
                    })

    return {
        "duplicate_osm_id_records": duplicate_osm_id_records,
        "duplicate_osm_id_values": duplicate_osm_id_values,
        "duplicate_location_name_records": duplicate_location_name_records,
        "duplicate_location_name_groups": duplicate_location_name_groups,
    }


def generate_record_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate record-level quality flags for each cafe.

    Args:
        df: DataFrame with cafe data

    Returns:
        New DataFrame with 'quality_flags' column added (original not modified)
    """
    result = df.copy()
    flags_list = []

    coord_validation = validate_coordinates(df)
    invalid_coords_by_index = {rec["index"]: rec["issues"] for rec in coord_validation["invalid_records"]}

    dup_result = detect_duplicates(df)
    dup_osm_indices = set()
    if "osm_id" in df.columns:
        valid_osm = df["osm_id"].notna() & (df["osm_id"] != "")
        dup_mask = df.loc[valid_osm, "osm_id"].duplicated(keep=False)
        dup_osm_indices = set(df.index[valid_osm][dup_mask].tolist())

    dup_loc_indices = set()
    for group in dup_result["duplicate_location_name_groups"]:
        dup_loc_indices.update(group["indices"])

    for idx in df.index:
        flags = []
        row = df.loc[idx]

        for field in ["name", "cuisine", "opening_hours", "website", "phone"]:
            if field in df.columns and is_missing(row.get(field)):
                flags.append(f"missing_{field}")

        if idx in invalid_coords_by_index:
            for issue in invalid_coords_by_index[idx]:
                if issue in ("missing_latitude", "latitude_out_of_range", "non_numeric_latitude"):
                    flags.append("invalid_latitude")
                elif issue in ("missing_longitude", "longitude_out_of_range", "non_numeric_longitude"):
                    flags.append("invalid_longitude")

        if idx in dup_osm_indices:
            flags.append("duplicate_osm_id")

        if idx in dup_loc_indices:
            flags.append("duplicate_location_name")

        flags_list.append(flags)

    result["quality_flags"] = flags_list
    result["quality_issue_count"] = [len(f) for f in flags_list]

    return result


def generate_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    """
    Generate a structured quality report for the dataset.

    Args:
        df: DataFrame with cafe data

    Returns:
        Dictionary with quality report
    """
    completeness = calculate_completeness(df)
    coord_validation = validate_coordinates(df)
    dup_result = detect_duplicates(df)

    field_completeness = {}
    for field, metrics in completeness.items():
        field_completeness[field] = {
            "present": metrics["present_count"],
            "missing": metrics["missing_count"],
            "completeness_percentage": metrics["completeness_percentage"],
        }

    return {
        "total_records": len(df),
        "valid_coordinate_records": coord_validation["valid_count"],
        "invalid_coordinate_records": coord_validation["invalid_count"],
        "duplicate_osm_id_records": dup_result["duplicate_osm_id_records"],
        "duplicate_location_name_records": dup_result["duplicate_location_name_records"],
        "field_completeness": field_completeness,
    }


def generate_provenance(
    df: pd.DataFrame,
    source_file: str | None = None,
) -> dict[str, Any]:
    """
    Generate provenance information for the dataset.

    Args:
        df: DataFrame with cafe data
        source_file: Optional path to source file

    Returns:
        Dictionary with provenance information
    """
    return {
        "source": SOURCE,
        "retrieval_method": RETRIEVAL_METHOD,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(df),
        "source_file": source_file,
    }


def load_data(csv_path: Path) -> pd.DataFrame:
    """
    Load the cafes CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        DataFrame with the cafe data

    Raises:
        FileNotFoundError: If CSV file doesn't exist
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8")
    return df


def format_quality_report(report: dict[str, Any], provenance: dict[str, Any]) -> str:
    """Format quality report for CLI display."""
    lines = []
    lines.append("=" * 50)
    lines.append("LUCKNOW CAFE FINDER - DATA QUALITY")
    lines.append("=" * 50)

    lines.append(f"\nDataset:")
    lines.append(f"  Records: {report['total_records']}")

    lines.append(f"\nCoordinates:")
    lines.append(f"  Valid: {report['valid_coordinate_records']}")
    lines.append(f"  Invalid: {report['invalid_coordinate_records']}")

    lines.append(f"\nDuplicates:")
    lines.append(f"  Duplicate OSM IDs: {report['duplicate_osm_id_records']}")
    lines.append(f"  Duplicate location/name records: {report['duplicate_location_name_records']}")

    lines.append(f"\nCompleteness:")
    for field in IMPORTANT_FIELDS:
        if field in report["field_completeness"]:
            fc = report["field_completeness"][field]
            lines.append(f"  {field.replace('_', ' ').title()}: {fc['completeness_percentage']:.1f}%")

    lines.append(f"\nProvenance:")
    lines.append(f"  Source: {provenance['source']}")
    lines.append(f"  Retrieval method: {provenance['retrieval_method']}")
    if provenance.get("retrieved_at"):
        lines.append(f"  Retrieved at: {provenance['retrieved_at']}")
    if provenance.get("source_file"):
        lines.append(f"  Source file: {provenance['source_file']}")

    return "\n".join(lines)


def format_verbose_report(flags_df: pd.DataFrame) -> str:
    """Format verbose record-level quality issues."""
    lines = []
    lines.append("\n" + "=" * 50)
    lines.append("RECORD-LEVEL QUALITY ISSUES (VERBOSE)")
    lines.append("=" * 50)

    has_issues = False
    for _, row in flags_df.iterrows():
        flags = row.get("quality_flags", [])
        if flags:
            has_issues = True
            osm_id = row.get("osm_id", f"index_{row.name}")
            lines.append(f"\nRecord: {osm_id}")
            lines.append("  Issues:")
            for flag in flags:
                lines.append(f"    - {flag}")

    if not has_issues:
        lines.append("\nNo record-level issues found.")

    return "\n".join(lines)


def main() -> None:
    """Command-line entry point for data quality report."""
    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Data Quality & Provenance"
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show record-level quality issues",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)

    print("Lucknow Cafe Finder - Data Quality & Provenance")
    print(f"Loading data from: {csv_path}")

    try:
        df = load_data(csv_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    report = generate_quality_report(df)
    provenance = generate_provenance(df, source_file=str(csv_path))

    print(format_quality_report(report, provenance))

    if args.verbose:
        flags_df = generate_record_quality_flags(df)
        print(format_verbose_report(flags_df))


if __name__ == "__main__":
    main()
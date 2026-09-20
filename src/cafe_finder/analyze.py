"""Exploratory Data Analysis for Lucknow Cafe Finder dataset."""

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from cafe_finder.config import DEFAULT_CSV_PATH

REPORT_WIDTH = 50

REPORT_WIDTH = 50

IMPORTANT_FIELDS = [
    "name",
    "latitude",
    "longitude",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
    "street",
    "housenumber",
    "city",
    "postcode",
]


def load_csv(csv_path: Path) -> pd.DataFrame:
    """
    Load the cafes CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        DataFrame with the cafe data

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        pd.errors.EmptyDataError: If CSV is empty
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8")

    if df.empty:
        raise pd.errors.EmptyDataError("CSV file is empty")

    return df


def format_header(title: str) -> str:
    """Format a section header."""
    return f"\n{'=' * REPORT_WIDTH}\n{title}\n{'=' * REPORT_WIDTH}"


def format_subheader(title: str) -> str:
    """Format a subsection header."""
    return f"\n{'-' * REPORT_WIDTH}\n{title}\n{'-' * REPORT_WIDTH}"


def dataset_overview(df: pd.DataFrame) -> str:
    """Generate dataset overview section."""
    lines = [format_header("DATASET OVERVIEW")]

    lines.append(f"\nTotal cafes: {len(df)}")
    lines.append(f"Total columns: {len(df.columns)}")
    lines.append(f"\nColumn names: {', '.join(df.columns.tolist())}")

    lines.append("\nData types:")
    for col, dtype in df.dtypes.items():
        lines.append(f"  {col}: {dtype}")

    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    lines.append(f"\nMemory usage: {memory_mb:.2f} MB")

    return "\n".join(lines)


def data_completeness(df: pd.DataFrame) -> str:
    """Generate data completeness section."""
    lines = [format_header("DATA COMPLETENESS")]

    for field in IMPORTANT_FIELDS:
        if field in df.columns:
            present = df[field].notna().sum()
            missing = df[field].isna().sum()
            total = len(df)
            pct_missing = (missing / total) * 100 if total > 0 else 0
            lines.append(f"{field:<20} {present}/{total} present ({pct_missing:.1f}% missing)")
        else:
            lines.append(f"{field:<20} COLUMN NOT FOUND")

    return "\n".join(lines)


def cafe_names_analysis(df: pd.DataFrame) -> str:
    """Generate cafe names analysis section."""
    lines = [format_header("CAFE NAMES ANALYSIS")]

    if "name" not in df.columns:
        lines.append("Name column not found in dataset.")
        return "\n".join(lines)

    has_name = df["name"].notna().sum()
    missing_name = df["name"].isna().sum()
    total = len(df)

    lines.append(f"\nRecords with names: {has_name}/{total}")
    lines.append(f"Records without names: {missing_name}/{total}")

    if has_name > 0:
        name_counts = df["name"].value_counts()
        duplicate_names = name_counts[name_counts > 1]

        if len(duplicate_names) > 0:
            lines.append(f"\nDuplicate names found: {len(duplicate_names)} unique names appear multiple times")
            lines.append("\nMost common names:")
            for name, count in duplicate_names.head(10).items():
                lines.append(f"  {name}: {count} occurrences")
        else:
            lines.append("\nNo duplicate names found (all names are unique)")

    return "\n".join(lines)


def cuisine_analysis(df: pd.DataFrame) -> str:
    """Generate cuisine analysis section."""
    lines = [format_header("CUISINE ANALYSIS")]

    if "cuisine" not in df.columns:
        lines.append("Cuisine column not found in dataset.")
        return "\n".join(lines)

    has_cuisine = df["cuisine"].notna().sum()
    missing_cuisine = df["cuisine"].isna().sum()
    total = len(df)

    lines.append(f"\nRecords with cuisine: {has_cuisine}/{total}")
    lines.append(f"Records without cuisine: {missing_cuisine}/{total}")

    if has_cuisine > 0:
        all_cuisines = []
        for cuisine_str in df["cuisine"].dropna():
            if isinstance(cuisine_str, str) and cuisine_str.strip():
                parts = [c.strip() for c in cuisine_str.split(";")]
                all_cuisines.extend(parts)

        if all_cuisines:
            cuisine_series = pd.Series(all_cuisines)
            unique_cuisines = cuisine_series.nunique()
            lines.append(f"\nUnique cuisine types (after splitting on ';'): {unique_cuisines}")
            lines.append("\nMost common cuisine types:")
            for cuisine, count in cuisine_series.value_counts().head(15).items():
                lines.append(f"  {cuisine}: {count}")
        else:
            lines.append("\nNo parseable cuisine values found")

    return "\n".join(lines)


def website_analysis(df: pd.DataFrame) -> str:
    """Generate website analysis section."""
    lines = [format_header("WEBSITE ANALYSIS")]

    if "website" not in df.columns:
        lines.append("Website column not found in dataset.")
        return "\n".join(lines)

    has_website = df["website"].notna().sum()
    missing_website = df["website"].isna().sum()
    total = len(df)
    pct = (has_website / total) * 100 if total > 0 else 0

    lines.append(f"\nCafes with website: {has_website}/{total} ({pct:.1f}%)")
    lines.append(f"Cafes without website: {missing_website}/{total} ({100 - pct:.1f}%)")

    return "\n".join(lines)


def phone_analysis(df: pd.DataFrame) -> str:
    """Generate phone analysis section."""
    lines = [format_header("PHONE ANALYSIS")]

    if "phone" not in df.columns:
        lines.append("Phone column not found in dataset.")
        return "\n".join(lines)

    has_phone = df["phone"].notna().sum()
    missing_phone = df["phone"].isna().sum()
    total = len(df)
    pct = (has_phone / total) * 100 if total > 0 else 0

    lines.append(f"\nCafes with phone: {has_phone}/{total} ({pct:.1f}%)")
    lines.append(f"Cafes without phone: {missing_phone}/{total} ({100 - pct:.1f}%)")

    return "\n".join(lines)


def opening_hours_analysis(df: pd.DataFrame) -> str:
    """Generate opening hours analysis section."""
    lines = [format_header("OPENING HOURS ANALYSIS")]

    if "opening_hours" not in df.columns:
        lines.append("Opening hours column not found in dataset.")
        return "\n".join(lines)

    has_hours = df["opening_hours"].notna().sum()
    missing_hours = df["opening_hours"].isna().sum()
    total = len(df)
    pct = (has_hours / total) * 100 if total > 0 else 0

    lines.append(f"\nCafes with opening hours: {has_hours}/{total} ({pct:.1f}%)")
    lines.append(f"Cafes without opening hours: {missing_hours}/{total} ({100 - pct:.1f}%)")

    return "\n".join(lines)


def geographic_analysis(df: pd.DataFrame) -> str:
    """Generate geographic analysis section."""
    lines = [format_header("GEOGRAPHIC SUMMARY")]

    if "latitude" not in df.columns or "longitude" not in df.columns:
        lines.append("Latitude/longitude columns not found in dataset.")
        return "\n".join(lines)

    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")

    valid_lat = lat.notna().sum()
    valid_lon = lon.notna().sum()

    lines.append(f"\nValid latitude records: {valid_lat}/{len(df)}")
    lines.append(f"Valid longitude records: {valid_lon}/{len(df)}")

    if valid_lat > 0 and valid_lon > 0:
        lines.append(f"\nLatitude range: {lat.min():.6f} to {lat.max():.6f}")
        lines.append(f"Longitude range: {lon.min():.6f} to {lon.max():.6f}")

        lines.append(f"\nGeographic bounding box:")
        lines.append(f"  South (min lat): {lat.min():.6f}")
        lines.append(f"  North (max lat): {lat.max():.6f}")
        lines.append(f"  West (min lon):  {lon.min():.6f}")
        lines.append(f"  East (max lon):  {lon.max():.6f}")

        lat_span = lat.max() - lat.min()
        lon_span = lon.max() - lon.min()
        lines.append(f"\nLatitudinal span:  {lat_span:.6f} degrees")
        lines.append(f"Longitudinal span: {lon_span:.6f} degrees")
        lines.append("\nNote: This bounding range reflects the dataset's coverage,")
        lines.append("not necessarily the official city boundary.")

    return "\n".join(lines)


def address_completeness(df: pd.DataFrame) -> str:
    """Generate address completeness section."""
    lines = [format_header("ADDRESS COMPLETENESS")]

    address_fields = ["street", "housenumber", "city", "postcode"]
    available_fields = [f for f in address_fields if f in df.columns]

    if not available_fields:
        lines.append("No address columns found in dataset.")
        return "\n".join(lines)

    lines.append("\nAddress field availability:")
    for field in available_fields:
        present = df[field].notna().sum()
        missing = df[field].isna().sum()
        total = len(df)
        pct = (present / total) * 100 if total > 0 else 0
        lines.append(f"  {field:<15} {present}/{total} present ({pct:.1f}%)")

    full_address = df[available_fields].notna().all(axis=1).sum() if available_fields else 0
    lines.append(f"\nRecords with all address fields: {full_address}/{len(df)}")

    return "\n".join(lines)


def generate_report(df: pd.DataFrame) -> str:
    """Generate the complete EDA report."""
    sections = [
        dataset_overview(df),
        data_completeness(df),
        cafe_names_analysis(df),
        cuisine_analysis(df),
        website_analysis(df),
        phone_analysis(df),
        opening_hours_analysis(df),
        geographic_analysis(df),
        address_completeness(df),
    ]

    report = "\n".join(sections)
    report += f"\n\n{'=' * REPORT_WIDTH}\nEND OF REPORT\n{'=' * REPORT_WIDTH}\n"

    return report


def main() -> None:
    """Command-line entry point for EDA."""
    parser = argparse.ArgumentParser(description="Lucknow Cafe Finder - EDA Report")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file (default: {DEFAULT_CSV_PATH})",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)

    print("Lucknow Cafe Finder - Exploratory Data Analysis")
    print(f"Loading data from: {csv_path}")

    try:
        df = load_csv(csv_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    report = generate_report(df)
    print(report)


if __name__ == "__main__":
    main()
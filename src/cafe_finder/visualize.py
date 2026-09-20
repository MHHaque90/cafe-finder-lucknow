"""Data visualization for Lucknow Cafe Finder dataset."""

import argparse
import sys
from pathlib import Path

from cafe_finder.config import DEFAULT_CSV_PATH, DEFAULT_OUTPUT_DIR
from cafe_finder.quality import is_missing

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import pandas as pd

COMPLETENESS_FIELDS = [
    "name",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
]

REPORT_WIDTH = 50

IMPORTANT_FIELDS = [
    "name",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
]


def load_data(csv_path: Path | str | None = None) -> pd.DataFrame:
    """Load cafe data from CSV file."""
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8")
    if df.empty:
        raise pd.errors.EmptyDataError("CSV file is empty")
    return df


def prepare_coordinates(df: pd.DataFrame) -> tuple[list[float], list[float]]:
    """Prepare valid coordinate series from DataFrame."""
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return [], []

    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")

    valid = lat.notna() & lon.notna() & (lat.fillna(0).abs() != 0) & (lon.fillna(0).abs() != 0)
    return lat[valid].tolist(), lon[valid].tolist()


def prepare_cuisine_counts(df: pd.DataFrame) -> pd.Series:
    """Count cuisine types from semicolon-separated values."""
    if "cuisine" not in df.columns:
        return pd.Series(dtype=int)
    counts: pd.Series = pd.Series(dtype=int)
    for cuisine_str in df["cuisine"].dropna():
        if isinstance(cuisine_str, str) and cuisine_str.strip():
            parts = [c.strip() for c in cuisine_str.split(";")]
            for part in parts:
                part = part.strip()
                if part:
                    counts[part] = counts.get(part, 0) + 1
    return counts


def calculate_completeness(df: pd.DataFrame) -> dict[str, float]:
    """Calculate completeness percentages for important fields."""
    total = len(df)
    result: dict[str, float] = {}
    for field in COMPLETENESS_FIELDS:
        if field in df.columns:
            missing = int(df[field].map(is_missing).sum())
            result[field] = ((total - missing) / total * 100) if total > 0 else 0.0
        else:
            result[field] = 0.0
    return result


def create_cuisine_chart(
    counts: pd.Series, output_path: Path | str | None = None, top_n: int = 10
) -> Path:
    """Create a bar chart of cuisine distribution."""
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT_DIR / "cuisine_distribution.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n])

    plt.figure(figsize=(10, 6))
    categories = list(sorted_counts.keys())
    values = list(sorted_counts.values())
    plt.bar(categories, values)
    plt.xlabel("Cuisine")
    plt.ylabel("Count")
    plt.title("Cuisine Distribution")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


def create_completeness_chart(
    completeness: dict[str, float],
    output_path: Path | str | None = None,
) -> Path:
    """Create a horizontal bar chart of data completeness."""
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT_DIR / "data_completeness.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = list(completeness.keys())
    values = [completeness[f] for f in fields]

    plt.figure(figsize=(10, max(6, len(fields) * 0.4)))
    plt.barh(fields, values)
    plt.xlabel("Completeness (%)")
    plt.title("Data Completeness")
    plt.xlim(0, 100)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


def create_location_chart(
    lats: list[float], lons: list[float], output_path: Path | str | None = None
) -> Path:
    """Create a scatter plot of cafe locations."""
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT_DIR / "cafe_locations.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.scatter(lons, lats, alpha=0.6)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Cafe Locations")
    plt.gca().set_aspect("equal")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


def main() -> None:
    """Command-line entry point for visualization."""
    parser = argparse.ArgumentParser(description="Lucknow Cafe Finder - Data Visualization")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for charts (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df = load_data(csv_path)
    except (FileNotFoundError, pd.errors.EmptyDataError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    lats, lons = prepare_coordinates(df)
    counts = prepare_cuisine_counts(df)
    completeness = calculate_completeness(df)

    create_location_chart(lats, lons, output_dir / "cafe_locations.png")
    create_cuisine_chart(counts, output_dir / "cuisine_distribution.png", top_n=10)
    create_completeness_chart(completeness, output_dir / "data_completeness.png")

    print(f"Charts saved to {output_dir}")
    print(f"  - cuisine_distribution.png")
    print(f"  - data_completeness.png")
    print(f"  - cafe_locations.png")


if __name__ == "__main__":
    main()
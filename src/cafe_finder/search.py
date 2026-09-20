"""Search and filtering for Lucknow Cafe Finder dataset."""

import argparse
import sys
from pathlib import Path

from cafe_finder.config import DEFAULT_CSV_PATH

import pandas as pd

from cafe_finder.distance import calculate_distances, haversine_distance
from cafe_finder.ranking import rank_cafes

SORTABLE_FIELDS = ["name", "latitude", "longitude", "distance", "score"]
FIELD_PRESENCE_FIELDS = ["website", "phone", "opening_hours"]


def load_data(csv_path: Path) -> pd.DataFrame:
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


def is_value_present(value) -> bool:
    """
    Check if a value is present (not missing/empty).

    Args:
        value: Value to check

    Returns:
        True if value is usable, False otherwise
    """
    if pd.isna(value):
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def search_by_name(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Filter cafes by name using case-insensitive partial matching.

    Args:
        df: DataFrame to filter
        query: Search query string

    Returns:
        Filtered DataFrame (copy, original not modified)
    """
    if not query or not query.strip():
        return df.copy()

    if "name" not in df.columns:
        return df.iloc[0:0].copy()

    mask = df["name"].astype(str).str.contains(query, case=False, na=False)
    return df[mask].copy()


def filter_by_cuisine(df: pd.DataFrame, cuisine_tag: str) -> pd.DataFrame:
    """
    Filter cafes by cuisine tag.

    Matches individual tags after splitting on semicolon.
    Case-insensitive exact tag matching.

    Args:
        df: DataFrame to filter
        cuisine_tag: Cuisine tag to match

    Returns:
        Filtered DataFrame (copy, original not modified)
    """
    if not cuisine_tag or not cuisine_tag.strip():
        return df.copy()

    if "cuisine" not in df.columns:
        return df.iloc[0:0].copy()

    tag = cuisine_tag.strip().lower()

    def has_cuisine_tag(cuisine_str) -> bool:
        if not is_value_present(cuisine_str):
            return False
        tags = [t.strip().lower() for t in str(cuisine_str).split(";")]
        return tag in tags

    mask = df["cuisine"].apply(has_cuisine_tag)
    return df[mask].copy()


def filter_by_field_presence(df: pd.DataFrame, field: str) -> pd.DataFrame:
    """
    Filter cafes by presence of a field.

    Args:
        df: DataFrame to filter
        field: Field name to check

    Returns:
        Filtered DataFrame (copy, original not modified)
    """
    if field not in df.columns:
        return df.iloc[0:0].copy()

    mask = df[field].apply(is_value_present)
    return df[mask].copy()


def apply_filters(
    df: pd.DataFrame,
    name_query: str | None = None,
    cuisine: str | None = None,
    has_website: bool = False,
    has_phone: bool = False,
    has_opening_hours: bool = False,
) -> pd.DataFrame:
    """
    Apply multiple filters with AND logic.

    Args:
        df: DataFrame to filter
        name_query: Name search query (optional)
        cuisine: Cuisine tag filter (optional)
        has_website: Require website field present
        has_phone: Require phone field present
        has_opening_hours: Require opening_hours field present

    Returns:
        Filtered DataFrame
    """
    result = df.copy()

    if name_query is not None:
        result = search_by_name(result, name_query)

    if cuisine is not None:
        result = filter_by_cuisine(result, cuisine)

    if has_website:
        result = filter_by_field_presence(result, "website")

    if has_phone:
        result = filter_by_field_presence(result, "phone")

    if has_opening_hours:
        result = filter_by_field_presence(result, "opening_hours")

    return result


def sort_results(df: pd.DataFrame, sort_by: str = "name") -> pd.DataFrame:
    """
    Sort results by specified field.

    Args:
        df: DataFrame to sort
        sort_by: Field to sort by (name, latitude, longitude)

    Returns:
        Sorted DataFrame
    """
    if sort_by not in SORTABLE_FIELDS:
        return df.copy()

    if df.empty:
        return df.copy()

    if sort_by == "name":
        return df.sort_values(by="name", na_position="last").copy()

    if sort_by in ("latitude", "longitude"):
        return df.sort_values(by=sort_by, na_position="last").copy()

    return df.copy()


def format_value(value) -> str:
    """
    Format a value for display.

    Args:
        value: Value to format

    Returns:
        Formatted string
    """
    if not is_value_present(value):
        return "Not available"
    return str(value).strip()


def format_address(row: pd.Series) -> str:
    """
    Format address from available address fields.

    Args:
        row: DataFrame row

    Returns:
        Formatted address string
    """
    parts = []
    for field in ["street", "housenumber", "city", "postcode"]:
        val = format_value(row.get(field))
        if val != "Not available":
            parts.append(val)
    return ", ".join(parts) if parts else "Not available"


def format_result(row: pd.Series) -> str:
    """
    Format a single cafe result for display.

    Args:
        row: DataFrame row

    Returns:
        Formatted string
    """
    lines = []
    name = format_value(row.get("name"))
    lines.append(f"  {name}")

    cuisine = format_value(row.get("cuisine"))
    if cuisine != "Not available":
        lines.append(f"   Cuisine: {cuisine}")

    address = format_address(row)
    if address != "Not available":
        lines.append(f"   Address: {address}")

    website = format_value(row.get("website"))
    if website != "Not available":
        lines.append(f"   Website: {website}")

    phone = format_value(row.get("phone"))
    if phone != "Not available":
        lines.append(f"   Phone: {phone}")

    lat = row.get("latitude")
    lon = row.get("longitude")
    if is_value_present(lat) and is_value_present(lon):
        lines.append(f"   Coordinates: {float(lat):.6f}, {float(lon):.6f}")

    distance = row.get("distance_km")
    if is_value_present(distance):
        lines.append(f"   Distance: {float(distance):.2f} km")

    return "\n".join(lines)


def format_results(df: pd.DataFrame) -> str:
    """
    Format multiple cafe results for display.

    Args:
        df: DataFrame of results

    Returns:
        Formatted string
    """
    if df.empty:
        return "No cafes matched your filters."

    lines = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        lines.append(f"{i}. {format_result(row)}")

    return "\n\n".join(lines)


def format_result_with_score(row: pd.Series) -> str:
    """
    Format a single cafe result with score breakdown for display.

    Args:
        row: DataFrame row

    Returns:
        Formatted string
    """
    lines = []
    name = format_value(row.get("name"))
    lines.append(f"  {name}")

    score_total = row.get("score_total")
    if is_value_present(score_total):
        lines.append(f"   Score: {int(score_total)}/100")

    distance = row.get("distance_km")
    if is_value_present(distance):
        lines.append(f"   Distance: {float(distance):.2f} km")

    reasons = row.get("score_reasons")
    if isinstance(reasons, list) and reasons:
        lines.append("   Why:")
        for reason in reasons:
            lines.append(f"   - {reason}")

    return "\n".join(lines)


def format_results_with_score(df: pd.DataFrame) -> str:
    """
    Format multiple cafe results with score breakdown for display.

    Args:
        df: DataFrame of results

    Returns:
        Formatted string
    """
    if df.empty:
        return "No cafes matched your filters."

    lines = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        lines.append(f"{i}. {format_result_with_score(row)}")

    return "\n\n".join(lines)


def print_filter_summary(
    name_query: str | None,
    cuisine: str | None,
    has_website: bool,
    has_phone: bool,
    has_opening_hours: bool,
) -> None:
    """Print the active filter summary."""
    filters = []
    if name_query:
        filters.append(f"  Name: {name_query}")
    if cuisine:
        filters.append(f"  Cuisine: {cuisine}")
    if has_website:
        filters.append("  Website: required")
    if has_phone:
        filters.append("  Phone: required")
    if has_opening_hours:
        filters.append("  Opening hours: required")

    if filters:
        print("Filters:")
        for f in filters:
            print(f)
    else:
        print("Filters: (none)")


def main() -> None:
    """Command-line entry point for search."""
    parser = argparse.ArgumentParser(
        description="Lucknow Cafe Finder - Search & Filter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cafe_finder.search --name coffee
  python -m cafe_finder.search --cuisine coffee_shop
  python -m cafe_finder.search --has-website
  python -m cafe_finder.search --cuisine coffee_shop --has-website
  python -m cafe_finder.search --name coffee --sort-by name
  python -m cafe_finder.search --lat 26.8467 --lon 80.9462
  python -m cafe_finder.search --lat 26.8467 --lon 80.9462 --radius 3
  python -m cafe_finder.search --cuisine coffee_shop --lat 26.8467 --lon 80.9462 --radius 5
        """,
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Search by name (case-insensitive partial match)",
    )
    parser.add_argument(
        "--cuisine",
        type=str,
        help="Filter by cuisine tag (exact tag match, case-insensitive)",
    )
    parser.add_argument(
        "--has-website",
        action="store_true",
        help="Only show cafes with website",
    )
    parser.add_argument(
        "--has-phone",
        action="store_true",
        help="Only show cafes with phone number",
    )
    parser.add_argument(
        "--has-opening-hours",
        action="store_true",
        help="Only show cafes with opening hours",
    )
    parser.add_argument(
        "--sort-by",
        type=str,
        choices=SORTABLE_FIELDS,
        default="name",
        help=f"Sort results by field (default: name)",
    )
    parser.add_argument(
        "--lat",
        type=float,
        help="Latitude for distance search (requires --lon)",
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Longitude for distance search (requires --lat)",
    )
    parser.add_argument(
        "--radius",
        type=float,
        help="Search radius in kilometres (requires --lat and --lon)",
    )

    args = parser.parse_args()

    # Validate empty name query
    if args.name is not None and not args.name.strip():
        print("Error: --name cannot be empty or whitespace only", file=sys.stderr)
        sys.exit(1)

    # Validate lat/lon combination
    if args.lat is not None and args.lon is None:
        print("Error: --lat requires --lon", file=sys.stderr)
        sys.exit(1)
    if args.lon is not None and args.lat is None:
        print("Error: --lon requires --lat", file=sys.stderr)
        sys.exit(1)

    # Validate radius
    if args.radius is not None and args.radius < 0:
        print("Error: --radius must be non-negative", file=sys.stderr)
        sys.exit(1)

    # Validate radius without location
    if args.radius is not None and (args.lat is None or args.lon is None):
        print("Error: --radius requires --lat and --lon", file=sys.stderr)
        sys.exit(1)

    # Validate invalid latitude
    if args.lat is not None and not (-90 <= args.lat <= 90):
        print(f"Error: Invalid latitude {args.lat}: must be in range [-90, 90]", file=sys.stderr)
        sys.exit(1)
    # Validate invalid longitude
    if args.lon is not None and not (-180 <= args.lon <= 180):
        print(f"Error: Invalid longitude {args.lon}: must be in range [-180, 180]", file=sys.stderr)
        sys.exit(1)

    # Validate distance sort requires location
    if args.sort_by == "distance" and (args.lat is None or args.lon is None):
        print("Error: --sort-by distance requires --lat and --lon", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(args.csv_path)

    print("========================================")
    print("LUCKNOW CAFE FINDER")
    print("========================================\n")

    try:
        df = load_data(csv_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    has_location = args.lat is not None and args.lon is not None

    # Apply existing filters
    results = apply_filters(
        df,
        name_query=args.name,
        cuisine=args.cuisine,
        has_website=args.has_website,
        has_phone=args.has_phone,
        has_opening_hours=args.has_opening_hours,
    )

    if has_location:
        # Calculate distances from user location
        results = calculate_distances(results, args.lat, args.lon)

        # Sort by distance if requested or default when location supplied
        if args.sort_by == "distance" or (args.sort_by == "name" and has_location):
            results = results.sort_values(by="distance_km", na_position="last").copy()

        # Apply radius filter
        if args.radius is not None:
            results = results[results["distance_km"] <= args.radius].copy()

    # Handle score sorting (CLI-owned)
    if args.sort_by == "score":
        results = rank_cafes(results, args.cuisine)
        # Create sort keys for deterministic tie-breaking
        # score_total desc, normalized name asc, osm_id asc
        results["_sort_name"] = results["name"].apply(
            lambda x: str(x).strip().lower() if is_value_present(x) else ""
        )
        results["_sort_osm_id"] = results["osm_id"].apply(
            lambda x: str(x).strip().lower() if is_value_present(x) else ""
        )
        results = results.sort_values(
            by=["score_total", "_sort_name", "_sort_osm_id"],
            ascending=[False, True, True],
            na_position="last",
        ).copy()
        # Remove temporary sort keys
        results = results.drop(columns=["_sort_name", "_sort_osm_id"])

    # Sort by the requested existing field (when no location)
    if not has_location and args.sort_by in ["name", "latitude", "longitude"]:
        results = sort_results(results, args.sort_by)

    # Print filter summary
    print_filter_summary(
        args.name,
        args.cuisine,
        args.has_website,
        args.has_phone,
        args.has_opening_hours,
    )

    if has_location:
        print()
        print("Location:")
        print(f"  Latitude: {args.lat}")
        print(f"  Longitude: {args.lon}")
        if args.radius is not None:
            print()
            print("Radius:")
            print(f"  {args.radius} km")

    print()
    print(f"Results: {len(results)}")
    print("----------------------------------------")
    if args.sort_by == "score":
        print(format_results_with_score(results))
    else:
        print(format_results(results))
    print("----------------------------------------")
    print(f"\n{len(results)} cafes found.")


if __name__ == "__main__":
    main()
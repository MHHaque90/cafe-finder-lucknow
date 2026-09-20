"""Data cleaning and normalization for cafe records."""

import re
from typing import Any

REQUIRED_FIELDS = ("osm_id", "latitude", "longitude")

WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str | None) -> str | None:
    """
    Normalize whitespace in a text field.

    - Strips leading/trailing whitespace
    - Collapses internal whitespace sequences to single space
    - Returns None if input is None or empty after stripping

    Args:
        text: Input text or None

    Returns:
        Normalized text or None
    """
    if text is None:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    return WHITESPACE_RE.sub(" ", stripped)


def normalize_text_field(text: str | None) -> str | None:
    """
    Normalize a text field for consistent storage.

    Preserves original casing (does not lower/upper case).
    Only normalizes whitespace and removes control characters.

    Args:
        text: Input text or None

    Returns:
        Normalized text or None
    """
    if text is None:
        return None

    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\t\n\r")
    return normalize_whitespace(cleaned)


def ensure_numeric(value: Any, field_name: str) -> float | None:
    """
    Convert a value to float if possible.

    Args:
        value: Value to convert
        field_name: Name of field (for error messages)

    Returns:
        Float value or None if conversion fails
    """
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_valid_coordinate(lat: float | None, lon: float | None) -> bool:
    """
    Check if latitude/longitude are valid.

    Valid ranges:
    - Latitude: [-90, 90]
    - Longitude: [-180, 180]
    - Not (0, 0) which is often a placeholder

    Args:
        lat: Latitude value
        lon: Longitude value

    Returns:
        True if coordinates are valid
    """
    if lat is None or lon is None:
        return False

    if not (-90 <= lat <= 90):
        return False

    if not (-180 <= lon <= 180):
        return False

    if lat == 0 and lon == 0:
        return False

    return True


def has_usable_identity(record: dict[str, Any]) -> bool:
    """
    Check if a record has a usable cafe identity.

    A record has usable identity if it has:
    - An OSM ID (required)
    - AND at least one of: name, valid coordinates

    Args:
        record: Cafe record dict

    Returns:
        True if record has usable identity
    """
    if not record.get("osm_id"):
        return False

    has_name = bool(record.get("name"))

    lat = ensure_numeric(record.get("latitude"), "latitude")
    lon = ensure_numeric(record.get("longitude"), "longitude")
    has_coords = is_valid_coordinate(lat, lon)

    return has_name or has_coords


def clean_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """
    Clean and normalize a single cafe record.

    Args:
        record: Raw cafe record from fetch stage

    Returns:
        Cleaned record dict, or None if record should be discarded
    """
    if not has_usable_identity(record):
        return None

    lat = ensure_numeric(record.get("latitude"), "latitude")
    lon = ensure_numeric(record.get("longitude"), "longitude")

    if not is_valid_coordinate(lat, lon):
        lat, lon = None, None

    cleaned = {
        "osm_id": record.get("osm_id"),
        "osm_type": record.get("osm_type"),
        "osm_version": record.get("osm_version"),
        "osm_timestamp": record.get("osm_timestamp"),
        "osm_changeset": record.get("osm_changeset"),
        "osm_user": record.get("osm_user"),
        "osm_uid": record.get("osm_uid"),
        "name": normalize_text_field(record.get("name")),
        "latitude": lat,
        "longitude": lon,
        "street": normalize_text_field(record.get("street")),
        "housenumber": normalize_text_field(record.get("housenumber")),
        "city": normalize_text_field(record.get("city")),
        "postcode": normalize_text_field(record.get("postcode")),
        "cuisine": normalize_text_field(record.get("cuisine")),
        "opening_hours": normalize_text_field(record.get("opening_hours")),
        "website": normalize_text_field(record.get("website")),
        "phone": normalize_text_field(record.get("phone")),
        "source": normalize_text_field(record.get("source")),
    }

    return cleaned


def deduplicate_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """
    Remove duplicate records using simple deterministic rules.

    Duplicate detection (in order of precedence):
    1. Exact OSM ID match (same type + ID)
    2. Exact coordinate + name match (rounded to 6 decimal places)

    Args:
        records: List of cleaned records

    Returns:
        Tuple of (deduplicated_records, duplicates_removed_count)
    """
    seen_osm_ids: set[str] = set()
    seen_coord_name: set[tuple[float, float, str]] = set()
    unique_records: list[dict[str, Any]] = []
    duplicates_removed = 0

    for record in records:
        osm_id = record.get("osm_id")
        if osm_id in seen_osm_ids:
            duplicates_removed += 1
            continue

        lat = record.get("latitude")
        lon = record.get("longitude")
        name = record.get("name") or ""

        if lat is not None and lon is not None:
            coord_key = (round(lat, 6), round(lon, 6), name)
            if coord_key in seen_coord_name:
                duplicates_removed += 1
                continue
            seen_coord_name.add(coord_key)

        seen_osm_ids.add(osm_id)
        unique_records.append(record)

    return unique_records, duplicates_removed


def clean_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Clean a list of records and remove duplicates.

    Args:
        records: List of raw records from fetch stage

    Returns:
        Tuple of (cleaned_records, stats_dict)
        stats_dict contains: 'input_count', 'cleaned_count', 'duplicates_removed', 'discarded_count'
    """
    input_count = len(records)

    cleaned = []
    discarded = 0

    for record in records:
        cleaned_record = clean_record(record)
        if cleaned_record is not None:
            cleaned.append(cleaned_record)
        else:
            discarded += 1

    deduplicated, duplicates_removed = deduplicate_records(cleaned)

    stats = {
        "input_count": input_count,
        "cleaned_count": len(cleaned),
        "duplicates_removed": duplicates_removed,
        "discarded_count": discarded,
        "output_count": len(deduplicated),
    }

    return deduplicated, stats


def main() -> None:
    """Command-line entry point for cleaning (reads from raw, writes cleaned JSON)."""
    import json
    import sys

    from cafe_finder.config import RAW_DIR, PROCESSED_DIR

    input_path = RAW_DIR / "lucknow_cafes_raw.json"
    output_path = RAW_DIR / "lucknow_cafes_cleaned.json"

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    cleaned, stats = clean_records(records)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Input: {stats['input_count']}")
    print(f"Cleaned: {stats['cleaned_count']}")
    print(f"Discarded (no usable identity): {stats['discarded_count']}")
    print(f"Duplicates removed: {stats['duplicates_removed']}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
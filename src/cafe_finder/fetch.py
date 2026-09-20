"""Fetch cafe data from OpenStreetMap Overpass API."""

import json
import time
from pathlib import Path
from typing import Any

import requests

from cafe_finder.config import RAW_DIR

DEFAULT_USER_AGENT = "LucknowCafeFinder/0.1 (+https://github.com/example/lucknow-cafe-finder; learning project)"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

LUCKNOW_BBOX = (26.50, 80.56, 27.16, 81.22)

OVERPASS_QUERY = """
[out:json][timeout:30];
nwr["amenity"="cafe"]({south},{west},{north},{east});
out center;
""".strip()


def build_overpass_query(
    south: float,
    west: float,
    north: float,
    east: float,
) -> str:
    """Build Overpass QL query string for the given bounding box."""
    return OVERPASS_QUERY.format(south=south, west=west, north=north, east=east)


def fetch_osm_data(
    url: str = OVERPASS_URL,
    query: str | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Fetch cafe data from Overpass API.

    Args:
        url: Overpass API endpoint URL
        query: Overpass QL query string (uses default Lucknow bbox if None)
        user_agent: User-Agent header for the request
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response from Overpass API

    Raises:
        requests.RequestException: On network or HTTP errors
        ValueError: If response is not valid JSON
    """
    if query is None:
        query = build_overpass_query(*LUCKNOW_BBOX)

    headers = {"User-Agent": user_agent}
    data = {"data": query}

    response = requests.post(url, data=data, headers=headers, timeout=timeout)
    response.raise_for_status()

    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from Overpass API: {e}") from e


def extract_elements(osm_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract element list from Overpass API response.

    Args:
        osm_response: Parsed JSON response from Overpass API

    Returns:
        List of OSM elements (nodes, ways, relations)
    """
    return osm_response.get("elements", [])


def get_element_coordinates(element: dict[str, Any]) -> tuple[float | None, float | None]:
    """
    Extract latitude and longitude from an OSM element.

    For nodes: uses 'lat' and 'lon' fields directly.
    For ways/relations: uses 'center' object if available.

    Args:
        element: OSM element dict

    Returns:
        Tuple of (latitude, longitude) or (None, None) if not available
    """
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]

    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return center["lat"], center["lon"]

    return None, None


def element_to_record(element: dict[str, Any]) -> dict[str, Any]:
    """
    Convert an OSM element to a flat record dict.

    Args:
        element: OSM element dict from Overpass response

    Returns:
        Flattened record with selected fields
    """
    tags = element.get("tags", {})
    lat, lon = get_element_coordinates(element)

    osm_id = f"{element['type']}{element['id']}"

    record = {
        "osm_id": osm_id,
        "osm_type": element["type"],
        "osm_version": element.get("version"),
        "osm_timestamp": element.get("timestamp"),
        "osm_changeset": element.get("changeset"),
        "osm_user": element.get("user"),
        "osm_uid": element.get("uid"),
        "name": tags.get("name"),
        "latitude": lat,
        "longitude": lon,
        "street": tags.get("addr:street"),
        "housenumber": tags.get("addr:housenumber"),
        "city": tags.get("addr:city"),
        "postcode": tags.get("addr:postcode"),
        "cuisine": tags.get("cuisine"),
        "opening_hours": tags.get("opening_hours"),
        "website": tags.get("website"),
        "phone": tags.get("phone"),
        "source": tags.get("source"),
        "raw_tags": tags,
    }

    return record


def fetch_lucknow_cafes(
    url: str = OVERPASS_URL,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """
    Fetch all cafes in Lucknow from OpenStreetMap.

    This is the main entry point for fetching data. It makes a single
    request to the Overpass API and returns a list of flattened records.

    Args:
        url: Overpass API endpoint URL
        user_agent: User-Agent header for the request
        timeout: Request timeout in seconds

    Returns:
        List of cafe records (one per OSM element)
    """
    osm_response = fetch_osm_data(url=url, user_agent=user_agent, timeout=timeout)
    elements = extract_elements(osm_response)
    records = [element_to_record(el) for el in elements]
    return records


def save_raw_data(
    records: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Save raw records to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def main() -> None:
    """Command-line entry point for fetching data."""
    import sys

    from cafe_finder.config import RAW_DIR

    output_path = RAW_DIR / "lucknow_cafes_raw.json"

    print("Fetching Lucknow cafes from OpenStreetMap...")
    start_time = time.time()

    try:
        records = fetch_lucknow_cafes()
    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Data error: {e}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"Fetched {len(records)} records in {elapsed:.1f}s")

    save_raw_data(records, output_path)
    print(f"Saved raw data to {output_path}")


if __name__ == "__main__":
    main()
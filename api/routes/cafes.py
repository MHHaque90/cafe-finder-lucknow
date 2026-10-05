"""Cafe discovery endpoints.

Thin adapters over :mod:`cafe_finder.search`, :mod:`cafe_finder.distance`
and :mod:`cafe_finder.ranking`. Query validation mirrors the CLI's
validation order and messages; result construction calls the same domain
functions in the same order, so API output matches CLI output.
"""

from fastapi import APIRouter, HTTPException, Query

import pandas as pd

from cafe_finder.distance import calculate_distances
from cafe_finder.ranking import rank_cafes
from cafe_finder.search import (
    SORTABLE_FIELDS,
    apply_filters,
    is_value_present,
    sort_results,
)
from ..dependencies import load_dataset
from ..schemas import CafeResult, SearchResponse
from ..serializers import serialize_records

router = APIRouter()


def _validate_search_params(
    name: str | None,
    lat: float | None,
    lon: float | None,
    radius: float | None,
    sort_by: str,
) -> None:
    """Validate search parameters with the CLI's rules.

    Raises:
        HTTPException: 400 with a controlled message on invalid input.
    """
    if sort_by not in SORTABLE_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by {sort_by!r}: must be one of {SORTABLE_FIELDS}",
        )
    if name is not None and not name.strip():
        raise HTTPException(
            status_code=400,
            detail="Error: --name cannot be empty or whitespace only",
        )
    if lat is not None and lon is None:
        raise HTTPException(status_code=400, detail="Error: --lat requires --lon")
    if lon is not None and lat is None:
        raise HTTPException(status_code=400, detail="Error: --lon requires --lat")
    if radius is not None and radius < 0:
        raise HTTPException(
            status_code=400, detail="Error: --radius must be non-negative"
        )
    if radius is not None and (lat is None or lon is None):
        raise HTTPException(
            status_code=400, detail="Error: --radius requires --lat and --lon"
        )
    if lat is not None and not (-90 <= lat <= 90):
        raise HTTPException(
            status_code=400,
            detail=f"Error: Invalid latitude {lat}: must be in range [-90, 90]",
        )
    if lon is not None and not (-180 <= lon <= 180):
        raise HTTPException(
            status_code=400,
            detail=f"Error: Invalid longitude {lon}: must be in range [-180, 180]",
        )
    if sort_by == "distance" and (lat is None or lon is None):
        raise HTTPException(
            status_code=400,
            detail="Error: --sort-by distance requires --lat and --lon",
        )


def _run_search(
    df: pd.DataFrame,
    name: str | None,
    cuisine: str | None,
    has_website: bool,
    has_phone: bool,
    has_opening_hours: bool,
    lat: float | None,
    lon: float | None,
    radius: float | None,
    sort_by: str,
) -> pd.DataFrame:
    """Execute the CLI's search pipeline over an already-loaded DataFrame.

    Mirrors ``search.main`` orchestration step for step — filters, then
    distances, then radius, then ranking, then sorting — by calling the
    same domain functions. No logic is reimplemented here.
    """
    results = apply_filters(
        df,
        name_query=name,
        cuisine=cuisine,
        has_website=has_website,
        has_phone=has_phone,
        has_opening_hours=has_opening_hours,
    )

    has_location = lat is not None and lon is not None
    if has_location:
        results = calculate_distances(results, lat, lon)
        if sort_by == "distance" or (sort_by == "name" and has_location):
            results = results.sort_values(by="distance_km", na_position="last").copy()
        if radius is not None:
            results = results[results["distance_km"] <= radius].copy()

    if sort_by == "score":
        results = rank_cafes(results, cuisine)
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
        results = results.drop(columns=["_sort_name", "_sort_osm_id"])

    if not has_location and sort_by in ["name", "latitude", "longitude"]:
        results = sort_results(results, sort_by)

    return results


@router.get("/cafes", response_model=SearchResponse)
def list_cafes(
    name: str | None = Query(default=None, description="Case-insensitive name substring"),
    cuisine: str | None = Query(default=None, description="Exact cuisine tag match"),
    has_website: bool = Query(default=False),
    has_phone: bool = Query(default=False),
    has_opening_hours: bool = Query(default=False),
) -> SearchResponse:
    """List cafes with the CLI's filter semantics (AND logic, name sort)."""
    if name is not None and not name.strip():
        raise HTTPException(
            status_code=400,
            detail="Error: --name cannot be empty or whitespace only",
        )
    df = load_dataset()
    results = apply_filters(
        df,
        name_query=name,
        cuisine=cuisine,
        has_website=has_website,
        has_phone=has_phone,
        has_opening_hours=has_opening_hours,
    )
    results = sort_results(results, "name")
    records = serialize_records(results)
    return SearchResponse(
        count=len(records), results=[CafeResult(**record) for record in records]
    )


@router.get("/search", response_model=SearchResponse)
def search_cafes(
    name: str | None = Query(default=None),
    cuisine: str | None = Query(default=None),
    has_website: bool = Query(default=False),
    has_phone: bool = Query(default=False),
    has_opening_hours: bool = Query(default=False),
    lat: float | None = Query(default=None, description="Latitude in [-90, 90]"),
    lon: float | None = Query(default=None, description="Longitude in [-180, 180]"),
    radius: float | None = Query(default=None, description="Radius in kilometres"),
    sort_by: str = Query(default="name"),
) -> SearchResponse:
    """Search, filter, locate, and rank cafes via the domain pipeline."""
    _validate_search_params(name, lat, lon, radius, sort_by)
    df = load_dataset()
    results = _run_search(
        df, name, cuisine, has_website, has_phone, has_opening_hours,
        lat, lon, radius, sort_by,
    )
    records = serialize_records(results)
    return SearchResponse(
        count=len(records), results=[CafeResult(**record) for record in records]
    )


@router.get("/cafes/{osm_id}", response_model=CafeResult)
def get_cafe(
    osm_id: str,
    cuisine: str | None = Query(
        default=None,
        description="Optional cuisine tag: include deterministic ranking scores via rank_cafes",
    ),
) -> CafeResult:
    """Return the stored record for one stable ``osm_id``.

    Without ``cuisine`` the record is served as stored. With ``cuisine``
    the record is additionally passed through the existing
    :func:`rank_cafes` scorer, so ranking fields come from the same
    engine as search results — never computed in the API layer.
    """
    if not osm_id or not osm_id.strip():
        raise HTTPException(status_code=404, detail="Unknown osm_id")
    df = load_dataset()
    matches = df[df["osm_id"] == osm_id]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Unknown osm_id: {osm_id}")
    record_df = matches.head(1)
    if cuisine is not None:
        record_df = rank_cafes(record_df, cuisine)
    record = serialize_records(record_df)[0]
    return CafeResult(**record)

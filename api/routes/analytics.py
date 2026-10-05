"""Structured analytics endpoints.

Exposes the existing structured data builders
(:mod:`cafe_finder.visualize` prepare functions and
:mod:`cafe_finder.quality` completeness) as chart-ready JSON.
Human-readable prose reports stay CLI-only; PNG chart generation
stays out of the web path — the future frontend renders its own charts.
"""

from fastapi import APIRouter

from cafe_finder.visualize import (
    calculate_completeness as visualize_completeness,
)
from cafe_finder.visualize import (
    prepare_coordinates,
    prepare_cuisine_counts,
)
from ..dependencies import load_dataset
from ..schemas import (
    AnalyticsOverview,
    AnalyticsResponse,
    CoordinateBounds,
    Coordinates,
    CuisineCount,
)
from ..serializers import to_jsonable

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics() -> AnalyticsResponse:
    """Return overview, cuisine, completeness, and coordinate analytics."""
    df = load_dataset()

    counts = prepare_cuisine_counts(df)
    cuisine = [
        CuisineCount(tag=str(tag), count=int(to_jsonable(count)))
        for tag, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]

    completeness = {
        str(field): float(value)
        for field, value in visualize_completeness(df).items()
    }

    lats, lons = prepare_coordinates(df)
    lats = [float(value) for value in lats]
    lons = [float(value) for value in lons]
    bounds = None
    if lats and lons:
        bounds = CoordinateBounds(
            min_latitude=min(lats),
            max_latitude=max(lats),
            min_longitude=min(lons),
            max_longitude=max(lons),
        )

    return AnalyticsResponse(
        overview=AnalyticsOverview(
            total_records=len(df), columns=[str(col) for col in df.columns]
        ),
        cuisine=cuisine,
        completeness=completeness,
        coordinates=Coordinates(count=len(lats), latitudes=lats, longitudes=lons, bounds=bounds),
    )

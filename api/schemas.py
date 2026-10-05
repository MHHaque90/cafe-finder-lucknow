"""Pydantic response models for the Cafe Finder read API.

These DTOs describe HTTP output shapes only. Domain behavior stays in
``src/cafe_finder/``; models here never implement filtering, scoring,
or validation beyond transport-level types.
"""

from pydantic import BaseModel, Field


class CafeResult(BaseModel):
    """One cafe record as served by the API.

    Score and distance fields are present only when the query that
    produced the record requested them (location and/or score sorting),
    mirroring the CLI, which adds those columns conditionally.
    """

    osm_id: str
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    street: str | None = None
    housenumber: str | None = None
    city: str | None = None
    postcode: str | None = None
    cuisine: str | None = None
    opening_hours: str | None = None
    website: str | None = None
    phone: str | None = None
    source: str | None = None
    distance_km: float | None = None
    score_distance: int | None = None
    score_cuisine: int | None = None
    score_opening_hours: int | None = None
    score_website: int | None = None
    score_phone: int | None = None
    score_total: int | None = None
    score_reasons: list[str] | None = None


class SearchResponse(BaseModel):
    """Filtered (and optionally ranked) search results."""

    count: int
    results: list[CafeResult]


class CuisineCount(BaseModel):
    tag: str
    count: int


class CoordinateBounds(BaseModel):
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


class Coordinates(BaseModel):
    count: int
    latitudes: list[float]
    longitudes: list[float]
    bounds: CoordinateBounds | None = None


class AnalyticsOverview(BaseModel):
    total_records: int
    columns: list[str]


class AnalyticsResponse(BaseModel):
    overview: AnalyticsOverview
    cuisine: list[CuisineCount]
    completeness: dict[str, float]
    coordinates: Coordinates


class QualityRecordFlags(BaseModel):
    osm_id: str | None = None
    quality_flags: list[str] = Field(default_factory=list)
    quality_issue_count: int = 0


class QualityResponse(BaseModel):
    """Structured quality report.

    Deliberately contains no aggregate quality score: the project
    measures completeness, validity, and duplicates separately.
    """

    report: dict
    provenance: dict
    records: list[QualityRecordFlags]


class DatasetInfo(BaseModel):
    available: bool
    records: int


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    dataset: DatasetInfo


class ErrorResponse(BaseModel):
    detail: str

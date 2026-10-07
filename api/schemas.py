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


class SnapshotMetadata(BaseModel):
    """One successful snapshot's metadata, exactly as recorded."""

    snapshot_id: str
    retrieved_at_utc: str
    source: str
    retrieval_method: str
    endpoint: str
    query: str
    record_count: int
    raw_file: str
    processed_file: str
    status: str


class HistoryResponse(BaseModel):
    """Available snapshots plus the domain-computed history summary."""

    snapshots: list[SnapshotMetadata]
    summary: dict


class SnapshotDetailResponse(BaseModel):
    """One snapshot's metadata plus its read-only integrity verdict."""

    metadata: SnapshotMetadata
    integrity_status: str
    integrity_errors: list[str]


class ComparisonResponse(BaseModel):
    """Backend-computed dataset comparison. The API never fabricates rows:
    added/removed entries are the domain's serialized records, and an empty
    snapshot set is reported by the History endpoint, not here.
    """

    baseline: str
    target: str
    old_record_count: int
    new_record_count: int
    added: list[dict]
    removed: list[dict]
    modified: list[dict]
    unchanged: list[dict]
    field_changes: list[dict]


class SnapshotIntegrity(BaseModel):
    """Read-only snapshot integrity verdict. Absent snapshots are reported
    with a status such as NO_SNAPSHOTS, never converted to PASSED.
    """

    snapshot_id: str | None = None
    status: str
    checks: list = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SchemaValidation(BaseModel):
    """Current-dataset schema validation, as computed by the domain."""

    valid: bool
    schema_version: int
    missing_columns: list[str] = Field(default_factory=list)
    unexpected_columns: list[str] = Field(default_factory=list)
    invalid_types: dict[str, str] = Field(default_factory=dict)
    column_order_valid: bool


class ArtifactVerification(BaseModel):
    """Current-dataset artifact checks. No expectations are supplied, so
    only existence, readability, actual hash, and actual size are reported.
    """

    path: str
    exists: bool
    readable: bool
    sha256_actual: str | None = None
    sha256_expected: str | None = None
    sha_match: bool | None = None
    size_actual: int | None = None
    size_expected: int | None = None
    size_match: bool | None = None
    valid: bool
    error: str | None = None


class IntegrityResponse(BaseModel):
    snapshot_integrity: SnapshotIntegrity
    schema: SchemaValidation
    artifact: ArtifactVerification


class LineageSnapshotEntry(BaseModel):
    snapshot_id: str
    retrieved_at_utc: str
    record_count: int
    raw_file: str
    processed_file: str


class LineageReport(BaseModel):
    analysis_type: str
    source: str
    retrieval_method: str
    snapshots_analyzed: int
    snapshot_ids: list[str]
    first_snapshot: LineageSnapshotEntry
    latest_snapshot: LineageSnapshotEntry
    snapshots: list[LineageSnapshotEntry]
    generated_at_utc: str


class LineageResponse(BaseModel):
    """Historical-analysis lineage. When no successful snapshots exist the
    domain cannot establish lineage, so available is False with the reason.
    """

    available: bool
    report: LineageReport | None = None
    reason: str | None = None

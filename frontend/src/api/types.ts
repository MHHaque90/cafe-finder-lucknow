/**
 * Types mirroring the FastAPI response schemas (see /openapi.json).
 * Optional score fields stay optional: the API only includes them when
 * the query requested location and/or score sorting, exactly like the CLI
 * only adds those columns conditionally. Missing values stay `null` in
 * the data model — the UI chooses how to label them.
 */
export type SortMode = 'name' | 'latitude' | 'longitude' | 'distance' | 'score';

export interface CafeResult {
  osm_id: string;
  name: string | null;
  latitude: number | null;
  longitude: number | null;
  street: string | null;
  housenumber: string | null;
  city: string | null;
  postcode: string | null;
  cuisine: string | null;
  opening_hours: string | null;
  website: string | null;
  phone: string | null;
  source: string | null;
  distance_km: number | null;
  score_distance: number | null;
  score_cuisine: number | null;
  score_opening_hours: number | null;
  score_website: number | null;
  score_phone: number | null;
  score_total: number | null;
  score_reasons: string[] | null;
}

export interface SearchResponse {
  count: number;
  results: CafeResult[];
}

/** Shape of FastAPI error bodies: `{ "detail": string }`. */
export interface ApiErrorShape {
  detail: string;
}

export interface SearchParams {
  name?: string;
  cuisine?: string;
  has_website?: boolean;
  has_phone?: boolean;
  has_opening_hours?: boolean;
  lat?: number;
  lon?: number;
  radius?: number;
  sort_by?: SortMode;
}

export interface HealthDataset {
  available: boolean;
  records: number;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  dataset: HealthDataset;
}

export interface QualityRecordFlags {
  osm_id: string | null;
  quality_flags: string[];
  quality_issue_count: number;
}

export interface QualityProvenance {
  source: string;
  retrieval_method: string;
  retrieved_at: string;
  record_count: number;
  source_file: string | null;
}

export interface QualityResponse {
  report: Record<string, unknown>;
  provenance: QualityProvenance;
  records: QualityRecordFlags[];
}

export interface CuisineCount {
  tag: string;
  count: number;
}

export interface CoordinateBounds {
  min_latitude: number;
  max_latitude: number;
  min_longitude: number;
  max_longitude: number;
}

export interface AnalyticsCoordinates {
  count: number;
  latitudes: number[];
  longitudes: number[];
  bounds: CoordinateBounds | null;
}

export interface AnalyticsOverview {
  total_records: number;
  columns: string[];
}

export interface AnalyticsResponse {
  overview: AnalyticsOverview;
  cuisine: CuisineCount[];
  completeness: Record<string, number>;
  coordinates: AnalyticsCoordinates;
}

/** One recorded snapshot, exactly as the backend recorded it. */
export interface SnapshotMetadata {
  snapshot_id: string;
  retrieved_at_utc: string;
  source: string;
  retrieval_method: string;
  endpoint: string;
  query: string;
  record_count: number;
  raw_file: string;
  processed_file: string;
  status: string;
}

export interface HistoryResponse {
  snapshots: SnapshotMetadata[];
  summary: Record<string, unknown>;
}

export interface SnapshotDetail {
  metadata: SnapshotMetadata;
  integrity_status: string;
  integrity_errors: string[];
}

export interface ComparisonResponse {
  baseline: string;
  target: string;
  old_record_count: number;
  new_record_count: number;
  added: Array<Record<string, unknown>>;
  removed: Array<Record<string, unknown>>;
  modified: Array<Record<string, unknown>>;
  unchanged: Array<Record<string, unknown>>;
  field_changes: Array<Record<string, unknown>>;
}

export interface SnapshotIntegrity {
  snapshot_id: string | null;
  status: string;
  checks: unknown[];
  errors: string[];
}

export interface SchemaValidation {
  valid: boolean;
  schema_version: number;
  missing_columns: string[];
  unexpected_columns: string[];
  invalid_types: Record<string, string>;
  column_order_valid: boolean;
}

export interface ArtifactVerification {
  path: string;
  exists: boolean;
  readable: boolean;
  sha256_actual: string | null;
  sha256_expected: string | null;
  sha_match: boolean | null;
  size_actual: number | null;
  size_expected: number | null;
  size_match: boolean | null;
  valid: boolean;
  error: string | null;
}

export interface IntegrityResponse {
  snapshot_integrity: SnapshotIntegrity;
  schema: SchemaValidation;
  artifact: ArtifactVerification;
}

export interface LineageSnapshotEntry {
  snapshot_id: string;
  retrieved_at_utc: string;
  record_count: number;
  raw_file: string;
  processed_file: string;
}

export interface LineageReport {
  analysis_type: string;
  source: string;
  retrieval_method: string;
  snapshots_analyzed: number;
  snapshot_ids: string[];
  first_snapshot: LineageSnapshotEntry;
  latest_snapshot: LineageSnapshotEntry;
  snapshots: LineageSnapshotEntry[];
  generated_at_utc: string;
}

export interface LineageResponse {
  available: boolean;
  report: LineageReport | null;
  reason: string | null;
}

/** Error thrown by the API client. Never carries tracebacks or paths. */
export class ApiRequestError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

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

/** Error thrown by the API client. Never carries tracebacks or paths. */
export class ApiRequestError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

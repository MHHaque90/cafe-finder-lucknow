/**
 * Single typed boundary for all HTTP requests to the Cafe Finder API.
 * No component may call fetch directly. The server remains authoritative
 * for filtering, distance, ranking, and sorting — this client only
 * transports parameters and parses responses.
 */
import type {
  AnalyticsResponse,
  ApiErrorShape,
  CafeResult,
  HealthResponse,
  QualityResponse,
  SearchParams,
  SearchResponse,
  SortMode,
} from './types.ts';
import { ApiRequestError } from './types.ts';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')
  ?? 'http://127.0.0.1:8000';

/**
 * Distinct cuisine tags present in the current dataset, lowercased and
 * sorted. Derived from the verified 33-record CSV (13 distinct raw tags;
 * `Tea`/`tea` collapse because the backend matches tags case-insensitively
 * after splitting on `;`). If the dataset gains tags, this list — not the
 * matching semantics — is what evolves.
 */
export const CUISINE_OPTIONS: readonly string[] = [
  'breakfast',
  'brunch',
  'burger',
  'coffee_shop',
  'noodle',
  'oriental',
  'pasta',
  'pizza',
  'rolls',
  'sandwich',
  'tea',
  'tea_shop',
];

export const SORT_OPTIONS: readonly { value: SortMode; label: string }[] = [
  { value: 'score', label: 'Score' },
  { value: 'distance', label: 'Distance' },
  { value: 'name', label: 'Name' },
  { value: 'latitude', label: 'Latitude' },
  { value: 'longitude', label: 'Longitude' },
];

async function request<T>(path: string, params: Record<string, string | number | boolean | undefined>): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    // Omit absent, empty, and false values: the API defaults missing
    // booleans to false, so this keeps URLs (and URL state) minimal.
    if (value === undefined || value === '' || value === false) continue;
    query.append(key, String(value));
  }
  const url = query.size > 0 ? `${BASE_URL}${path}?${query}` : `${BASE_URL}${path}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new ApiRequestError(
      'Unable to reach the Cafe Finder API. Check that it is running.',
      0,
    );
  }
  if (!response.ok) {
    let detail = `Request failed (status ${response.status})`;
    try {
      const body = (await response.json()) as Partial<ApiErrorShape>;
      if (body && typeof body.detail === 'string' && body.detail.length > 0) {
        detail = body.detail;
      }
    } catch {
      // Keep the status-based fallback; never surface parse errors.
    }
    throw new ApiRequestError(detail, response.status);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health', {});
}

export function getCafes(params: Omit<SearchParams, 'lat' | 'lon' | 'radius' | 'sort_by'>): Promise<SearchResponse> {
  return request<SearchResponse>('/api/cafes', params as Record<string, string | number | boolean | undefined>);
}

export function getAnalytics(): Promise<AnalyticsResponse> {
  return request<AnalyticsResponse>('/api/analytics', {});
}

export function searchCafes(params: SearchParams): Promise<SearchResponse> {
  return request<SearchResponse>('/api/search', params as Record<string, string | number | boolean | undefined>);
}

export function getCafe(osmId: string, cuisine?: string): Promise<CafeResult> {
  const params: Record<string, string | number | boolean | undefined> = {};
  if (cuisine !== undefined && cuisine !== '') params.cuisine = cuisine;
  return request<CafeResult>(`/api/cafes/${encodeURIComponent(osmId)}`, params);
}

export function getQuality(): Promise<QualityResponse> {
  return request<QualityResponse>('/api/quality', {});
}

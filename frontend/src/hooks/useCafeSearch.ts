/**
 * Discover-page search state.
 *
 * URL query parameters are the single source of truth for filters, so
 * refresh preserves the search and links reproduce it. The server remains
 * authoritative for all results: this hook only transports parameters
 * (debounced) and tracks request state. Pairing validation (lat/lon,
 * radius) is checked locally for fast feedback; everything else is
 * decided by the API.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { searchCafes } from '../api/client.ts';
import type { CafeResult, SortMode } from '../api/types.ts';
import { SORT_OPTIONS } from '../api/client.ts';

export interface DiscoverFilters {
  name: string;
  cuisine: string;
  hasWebsite: boolean;
  hasPhone: boolean;
  hasHours: boolean;
  lat: string;
  lon: string;
  radius: string;
  sortBy: SortMode;
}

export const DEFAULT_FILTERS: DiscoverFilters = {
  name: '',
  cuisine: '',
  hasWebsite: false,
  hasPhone: false,
  hasHours: false,
  lat: '',
  lon: '',
  radius: '',
  sortBy: 'score',
};

const SORT_VALUES: readonly string[] = SORT_OPTIONS.map((o) => o.value);

function parseFilters(search: string): DiscoverFilters {
  const params = new URLSearchParams(search);
  const sortBy = params.get('sort_by') ?? '';
  return {
    name: params.get('name') ?? '',
    cuisine: params.get('cuisine') ?? '',
    hasWebsite: params.get('has_website') === 'true',
    hasPhone: params.get('has_phone') === 'true',
    hasHours: params.get('has_opening_hours') === 'true',
    lat: params.get('lat') ?? '',
    lon: params.get('lon') ?? '',
    radius: params.get('radius') ?? '',
    sortBy: (SORT_VALUES as readonly string[]).includes(sortBy) ? (sortBy as SortMode) : 'score',
  };
}

function serializeFilters(filters: DiscoverFilters): string {
  const params = new URLSearchParams();
  if (filters.name.trim() !== '') params.set('name', filters.name.trim());
  if (filters.cuisine !== '') params.set('cuisine', filters.cuisine);
  if (filters.hasWebsite) params.set('has_website', 'true');
  if (filters.hasPhone) params.set('has_phone', 'true');
  if (filters.hasHours) params.set('has_opening_hours', 'true');
  if (filters.lat.trim() !== '') params.set('lat', filters.lat.trim());
  if (filters.lon.trim() !== '') params.set('lon', filters.lon.trim());
  if (filters.radius.trim() !== '') params.set('radius', filters.radius.trim());
  if (filters.sortBy !== 'score') params.set('sort_by', filters.sortBy);
  const query = params.toString();
  return query === '' ? window.location.pathname : `${window.location.pathname}?${query}`;
}

function parseNumber(raw: string): number | undefined | null {
  // undefined = absent; null = present but not a number.
  if (raw.trim() === '') return undefined;
  const value = Number(raw);
  return Number.isNaN(value) ? null : value;
}

export type SearchStatus = 'loading' | 'success' | 'empty' | 'error';

export interface SearchState {
  status: SearchStatus;
  results: CafeResult[];
  count: number;
  error: string | null;
}

export function useCafeSearch(debounceMs = 350): {
  filters: DiscoverFilters;
  updateFilters: (patch: Partial<DiscoverFilters>) => void;
  clearFilters: () => void;
  state: SearchState;
  retry: () => void;
} {
  const [filters, setFilters] = useState<DiscoverFilters>(() => parseFilters(window.location.search));
  const [state, setState] = useState<SearchState>({ status: 'loading', results: [], count: 0, error: null });
  const [nonce, setNonce] = useState(0);
  const requestId = useRef(0);

  const updateFilters = useCallback((patch: Partial<DiscoverFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const retry = useCallback(() => {
    setNonce((n) => n + 1);
  }, []);

  useEffect(() => {
    window.history.replaceState(null, '', serializeFilters(filters));
  }, [filters]);

  useEffect(() => {
    const lat = parseNumber(filters.lat);
    const lon = parseNumber(filters.lon);
    const radius = parseNumber(filters.radius);
    if (lat === null) {
      setState({ status: 'error', results: [], count: 0, error: 'Latitude must be a number.' });
      return;
    }
    if (lon === null) {
      setState({ status: 'error', results: [], count: 0, error: 'Longitude must be a number.' });
      return;
    }
    if (radius === null) {
      setState({ status: 'error', results: [], count: 0, error: 'Radius must be a number.' });
      return;
    }
    if ((lat === undefined) !== (lon === undefined)) {
      setState({
        status: 'error', results: [], count: 0,
        error: 'Latitude and longitude are required together.',
      });
      return;
    }
    if (radius !== undefined && (lat === undefined || lon === undefined)) {
      setState({
        status: 'error', results: [], count: 0,
        error: 'Radius requires latitude and longitude to be set.',
      });
      return;
    }

    const id = ++requestId.current;
    setState((prev) => ({ ...prev, status: 'loading', error: null }));
    const timer = window.setTimeout(() => {
      searchCafes({
        name: filters.name.trim() === '' ? undefined : filters.name.trim(),
        cuisine: filters.cuisine === '' ? undefined : filters.cuisine,
        has_website: filters.hasWebsite || undefined,
        has_phone: filters.hasPhone || undefined,
        has_opening_hours: filters.hasHours || undefined,
        lat,
        lon,
        radius,
        sort_by: filters.sortBy,
      })
        .then((body) => {
          if (id !== requestId.current) return;
          setState({
            status: body.count === 0 ? 'empty' : 'success',
            results: body.results,
            count: body.count,
            error: null,
          });
        })
        .catch((error: unknown) => {
          if (id !== requestId.current) return;
          setState({
            status: 'error',
            results: [],
            count: 0,
            error: error instanceof Error ? error.message : 'Unable to load cafes.',
          });
        });
    }, debounceMs);
    return () => {
      window.clearTimeout(timer);
    };
  }, [filters, nonce, debounceMs]);

  return { filters, updateFilters, clearFilters, state, retry };
}

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import App from './App.tsx';

const CAFE = {
  osm_id: 'node1', name: 'Cafe', latitude: 26.85, longitude: 80.94,
  street: null, housenumber: null, city: null, postcode: null, cuisine: 'tea',
  opening_hours: null, website: null, phone: null, source: null, distance_km: null,
  score_distance: 0, score_cuisine: 0, score_opening_hours: 0, score_website: 0,
  score_phone: 0, score_total: 0, score_reasons: [],
};

const SEARCH_BODY = { count: 1, results: [CAFE] };

const ANALYTICS_BODY = {
  overview: { total_records: 1, columns: ['osm_id'] },
  cuisine: [{ tag: 'tea', count: 1 }],
  completeness: { name: 100 },
  coordinates: {
    count: 1, latitudes: [26.85], longitudes: [80.94],
    bounds: { min_latitude: 26.85, max_latitude: 26.85, min_longitude: 80.94, max_longitude: 80.94 },
  },
};

const QUALITY_BODY = {
  report: {
    total_records: 1, valid_coordinate_records: 1, invalid_coordinate_records: 0,
    duplicate_osm_id_records: 0, duplicate_location_name_records: 0,
    field_completeness: { name: { present: 1, missing: 0, completeness_percentage: 100 } },
  },
  provenance: {
    source: 'OpenStreetMap', retrieval_method: 'Overpass API',
    retrieved_at: '2026-01-01T00:00:00+00:00', record_count: 1, source_file: null,
  },
  records: [{ osm_id: 'node1', quality_flags: [], quality_issue_count: 0 }],
};

const HISTORY_BODY = {
  snapshots: [],
  summary: {
    snapshots_analyzed: 0, snapshot_ids: [], first_snapshot: null, latest_snapshot: null,
    unique_cafes: 0, added: 0, no_longer_observed: 0, modified: 0, unchanged: 0,
    field_summary: [], total_field_changes: 0,
  },
};

const INTEGRITY_BODY = {
  snapshot_integrity: { snapshot_id: null, status: 'NO_SNAPSHOTS', checks: [], errors: [] },
  schema: {
    valid: true, schema_version: 1, missing_columns: [], unexpected_columns: [],
    invalid_types: {}, column_order_valid: true,
  },
  artifact: {
    path: 'data/processed/lucknow_cafes.csv', exists: true, readable: true,
    sha256_actual: null, sha256_expected: null, sha_match: null, size_actual: 1,
    size_expected: null, size_match: null, valid: true, error: null,
  },
};

const LINEAGE_BODY = { available: false, report: null, reason: 'none recorded' };

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      let body: unknown = SEARCH_BODY;
      if (path.includes('/api/analytics')) body = ANALYTICS_BODY;
      else if (path.includes('/api/quality')) body = QUALITY_BODY;
      else if (path.includes('/api/history')) body = HISTORY_BODY;
      else if (path.includes('/api/integrity')) body = INTEGRITY_BODY;
      else if (path.includes('/api/lineage')) body = LINEAGE_BODY;
      else if (path.includes('/api/cafes/')) body = CAFE;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
    }),
  );
}

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  window.location.hash = '';
  mockApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

const ROUTES: Array<{ hash: string; ready: RegExp }> = [
  { hash: '#/', ready: /1 cafe found/ },
  { hash: '#/cafes/node1', ready: /Record node1/ },
  { hash: '#/analytics', ready: /Cuisine distribution/ },
  { hash: '#/quality', ready: /Field completeness/ },
  { hash: '#/history', ready: /No historical snapshots are currently available/ },
  { hash: '#/history/compare', ready: /Snapshot comparison requires two available snapshots/ },
  { hash: '#/integrity', ready: /Snapshot integrity/ },
  { hash: '#/lineage', ready: /Current dataset provenance/ },
];

describe('axe accessibility audit', () => {
  it.each(ROUTES)('has no axe violations on $hash', async ({ hash, ready }) => {
    window.history.replaceState(null, '', '/');
    window.location.hash = hash;
    mockApi();
    const { container } = render(<App />);
    await waitFor(() => expect(screen.getByText(ready)).toBeInTheDocument());
    // Plain toEqual (not the vitest-axe matcher): this vitest-axe
    // version's packaged matcher registration is broken (its
    // dist/extend-expect.js ships empty), while the axe runner itself
    // works. An empty violations array is exactly what
    // toHaveNoViolations asserts.
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App.tsx';

const SEARCH_BODY = {
  count: 1,
  results: [
    {
      osm_id: 'node1', name: 'Cafe', latitude: 26.85, longitude: 80.94,
      street: null, housenumber: null, city: null, postcode: null, cuisine: 'tea',
      opening_hours: null, website: null, phone: null, source: null, distance_km: null,
      score_distance: 0, score_cuisine: 0, score_opening_hours: 0, score_website: 0,
      score_phone: 0, score_total: 0, score_reasons: [],
    },
  ],
};

const ANALYTICS_PAYLOAD = {
  overview: { total_records: 1, columns: ['osm_id'] },
  cuisine: [{ tag: 'tea', count: 1 }],
  completeness: { name: 100 },
  coordinates: {
    count: 1, latitudes: [26.85], longitudes: [80.94],
    bounds: { min_latitude: 26.85, max_latitude: 26.85, min_longitude: 80.94, max_longitude: 80.94 },
  },
};

const QUALITY_PAYLOAD = {
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

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      let body: unknown = SEARCH_BODY;
      if (path.includes('/api/analytics')) body = ANALYTICS_PAYLOAD;
      else if (path.includes('/api/quality')) body = QUALITY_PAYLOAD;
      else if (path.includes('/api/cafes/')) body = SEARCH_BODY.results[0];
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

describe('App navigation', () => {
  it('starts on Discover', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Find cafes' })).toBeInTheDocument();
  });

  it('navigates Discover to Analytics and back', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('link', { name: 'Analytics' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Analytics' })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('link', { name: 'Discover' }));
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
  });

  it('navigates Discover to Data Quality and back', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('link', { name: 'Data Quality' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Data Quality' })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('link', { name: 'Discover' }));
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
  });

  it('marks the active navigation link', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
    expect(screen.getByRole('link', { name: 'Discover' })).toHaveAttribute('aria-current', 'page');
    fireEvent.click(screen.getByRole('link', { name: 'Analytics' }));
    await waitFor(() =>
      expect(screen.getByRole('link', { name: 'Analytics' })).toHaveAttribute('aria-current', 'page'),
    );
  });

  it('keeps the detail route reachable by hash', async () => {
    window.location.hash = '#/cafes/node1';
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Record node1/)).toBeInTheDocument());
  });

  it('falls back to Discover for unknown hashes', async () => {
    window.location.hash = '#/nope';
    render(<App />);
    await waitFor(() => expect(screen.getByText('1 cafe found')).toBeInTheDocument());
  });
});

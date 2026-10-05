import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AnalyticsPage } from './AnalyticsPage.tsx';

const ANALYTICS = {
  overview: {
    total_records: 33,
    columns: ['osm_id', 'name', 'latitude', 'longitude', 'street', 'housenumber', 'city', 'postcode', 'cuisine', 'opening_hours', 'website', 'phone', 'source'],
  },
  cuisine: [
    { tag: 'coffee_shop', count: 10 },
    { tag: 'pasta', count: 2 },
  ],
  completeness: { name: 81.8, website: 6.1 },
  coordinates: {
    count: 33,
    latitudes: [26.85],
    longitudes: [80.94],
    bounds: { min_latitude: 26.79, max_latitude: 26.95, min_longitude: 80.88, max_longitude: 81.05 },
  },
};

const CAFES = {
  count: 1,
  results: [
    {
      osm_id: 'node1', name: 'Cafe', latitude: 26.85, longitude: 80.94,
      street: null, housenumber: null, city: null, postcode: null, cuisine: 'coffee_shop',
      opening_hours: null, website: null, phone: null, source: null, distance_km: null,
      score_distance: null, score_cuisine: null, score_opening_hours: null, score_website: null,
      score_phone: null, score_total: null, score_reasons: null,
    },
  ],
};

function mockApi(analyticsBody: unknown, cafesBody: unknown = CAFES, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      const body = path.includes('/api/analytics') ? analyticsBody : cafesBody;
      return Promise.resolve({ ok, status, json: () => Promise.resolve(body) });
    }),
  );
}

beforeEach(() => {
  mockApi(ANALYTICS);
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('AnalyticsPage', () => {
  it('shows a loading state first', () => {
    render(<AnalyticsPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders overview metrics from the API', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText('Total cafes')).toBeInTheDocument());
    expect(screen.getAllByText('33')).toHaveLength(2);
    expect(screen.getByText('Data columns')).toBeInTheDocument();
    expect(screen.getByText('Records with valid coordinates')).toBeInTheDocument();
  });

  it('renders cuisine data with values and an accessible table', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getAllByText('coffee_shop')).toHaveLength(2));
    expect(screen.getAllByText('10')).toHaveLength(2);
    expect(screen.getByRole('columnheader', { name: 'Cuisine tag' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Records' })).toBeInTheDocument();
  });

  it('renders completeness percentages as text', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getAllByText('81.8%')).toHaveLength(2));
    expect(screen.getAllByText('6.1%')).toHaveLength(2);
  });

  it('renders coordinate bounds and an explanation', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText(/33 of 33 records/)).toBeInTheDocument());
    expect(screen.getByText(/26\.7900/)).toBeInTheDocument();
  });

  it('shows an empty state for a zero-record dataset', async () => {
    mockApi({ ...ANALYTICS, overview: { total_records: 0, columns: [] } });
    render(<AnalyticsPage />);
    await waitFor(() =>
      expect(screen.getByText(/zero records/i)).toBeInTheDocument(),
    );
  });

  it('shows an error state with retry on API failure', async () => {
    mockApi({}, {}, false, 500);
    const calls: string[] = [];
    const stub = vi.mocked(fetch);
    stub.mockImplementation(((url: unknown) => {
      calls.push(String(url));
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ detail: 'down' }) });
    }) as unknown as typeof fetch);
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => expect(calls.length).toBeGreaterThan(2));
  });

  it('contains no fabricated metrics', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getAllByText('33')).toHaveLength(2));
    expect(screen.queryByText(/average rating/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/market share/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/popularity/i)).not.toBeInTheDocument();
  });
});

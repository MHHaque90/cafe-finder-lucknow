import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import type { CafeResult } from '../api/types.ts';
import { CafeDetailPage } from './CafeDetailPage.tsx';

const RECORD: CafeResult = {
  osm_id: 'node1',
  name: 'Cafe Coffee Day',
  latitude: 26.85,
  longitude: 80.94,
  street: 'Ashok Marg',
  housenumber: null,
  city: 'Lucknow',
  postcode: '226001',
  cuisine: 'coffee_shop',
  opening_hours: '09:00-22:00',
  website: 'https://example.org',
  phone: null,
  source: null,
  distance_km: null,
  score_distance: 0,
  score_cuisine: 30,
  score_opening_hours: 15,
  score_website: 10,
  score_phone: 0,
  score_total: 55,
  score_reasons: ['Cuisine match: coffee_shop → 30 points'],
};

const FLAGS = {
  records: [{ osm_id: 'node1', quality_flags: ['missing_phone'], quality_issue_count: 1 }],
  report: {},
  provenance: {
    source: 'OpenStreetMap',
    retrieval_method: 'Overpass API',
    retrieved_at: '2026-01-01T00:00:00+00:00',
    record_count: 33,
    source_file: 'data/processed/lucknow_cafes.csv',
  },
};

function mockApi(detail: { ok: boolean; status: number; body: unknown }) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      const body = path.includes('/api/quality') ? FLAGS : detail.body;
      const ok = path.includes('/api/quality') ? true : detail.ok;
      const status = path.includes('/api/quality') ? 200 : detail.status;
      return Promise.resolve({ ok, status, json: () => Promise.resolve(body) });
    }),
  );
}

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  mockApi({ ok: true, status: 200, body: RECORD });
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('CafeDetailPage', () => {
  it('shows a loading state first', () => {
    render(<CafeDetailPage osmId="node1" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders identity, metadata, score, flags, and provenance', async () => {
    render(<CafeDetailPage osmId="node1" />);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Cafe Coffee Day' })).toBeInTheDocument());
    expect(screen.getByText(/Record node1/)).toBeInTheDocument();
    expect(screen.getByText(/Score: 55\/100/)).toBeInTheDocument();
    expect(screen.getByText(/Cuisine match: coffee_shop → 30 points/)).toBeInTheDocument();
    expect(screen.getByText('missing_phone')).toBeInTheDocument();
    expect(screen.getByText(/Source: OpenStreetMap via Overpass API/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'https://example.org' })).toHaveAttribute(
      'target',
      '_blank',
    );
  });

  it('labels missing fields as unavailable', async () => {
    render(<CafeDetailPage osmId="node1" />);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Cafe Coffee Day' })).toBeInTheDocument());
    expect(screen.getByText(/Phone unavailable in dataset/)).toBeInTheDocument();
  });

  it('shows a 404 state for unknown ids', async () => {
    mockApi({ ok: false, status: 404, body: { detail: 'Unknown osm_id: nope' } });
    render(<CafeDetailPage osmId="nope" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText(/No cafe found for this ID/)).toBeInTheDocument();
  });

  it('shows an error state on API failure with a back link', async () => {
    mockApi({ ok: false, status: 500, body: { detail: 'Dataset unavailable' } });
    render(<CafeDetailPage osmId="node1" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText(/Unable to load this cafe/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to results/i })).toHaveAttribute('href', '#/');
  });

  it('offers a back-to-results link on success', async () => {
    render(<CafeDetailPage osmId="node1" />);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Cafe Coffee Day' })).toBeInTheDocument());
    expect(screen.getByRole('link', { name: /back to results/i })).toHaveAttribute('href', '#/');
  });
});

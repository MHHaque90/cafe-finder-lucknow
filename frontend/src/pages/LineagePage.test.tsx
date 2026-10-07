import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { LineagePage } from './LineagePage.tsx';

const QUALITY = {
  report: { total_records: 1 },
  provenance: {
    source: 'OpenStreetMap', retrieval_method: 'Overpass API',
    retrieved_at: '2026-01-01T00:00:00+00:00', record_count: 1,
    source_file: 'data/processed/lucknow_cafes.csv',
  },
  records: [],
};

const LINEAGE_UNAVAILABLE = {
  available: false,
  report: null,
  reason: 'No valid successful snapshots found; cannot establish historical-analysis lineage.',
};

const LINEAGE_AVAILABLE = {
  available: true,
  report: {
    analysis_type: 'historical_change_analysis',
    source: 'OpenStreetMap',
    retrieval_method: 'Overpass API',
    snapshots_analyzed: 2,
    snapshot_ids: ['2026-01-01T000000Z', '2026-02-01T000000Z'],
    first_snapshot: {
      snapshot_id: '2026-01-01T000000Z', retrieved_at_utc: '2026-01-01T00:00:00Z',
      record_count: 2, raw_file: 'raw.json', processed_file: 'cafes.csv',
    },
    latest_snapshot: {
      snapshot_id: '2026-02-01T000000Z', retrieved_at_utc: '2026-02-01T00:00:00Z',
      record_count: 2, raw_file: 'raw.json', processed_file: 'cafes.csv',
    },
    snapshots: [
      {
        snapshot_id: '2026-01-01T000000Z', retrieved_at_utc: '2026-01-01T00:00:00Z',
        record_count: 2, raw_file: 'raw.json', processed_file: 'cafes.csv',
      },
      {
        snapshot_id: '2026-02-01T000000Z', retrieved_at_utc: '2026-02-01T00:00:00Z',
        record_count: 2, raw_file: 'raw.json', processed_file: 'cafes.csv',
      },
    ],
    generated_at_utc: '2026-03-01T00:00:00Z',
  },
  reason: null,
};

function mockLineage(lineageBody: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      const body = path.includes('/api/lineage') ? lineageBody : QUALITY;
      return Promise.resolve({ ok, status, json: () => Promise.resolve(body) });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('LineagePage', () => {
  it('shows a loading state first', () => {
    mockLineage(LINEAGE_UNAVAILABLE);
    render(<LineagePage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('reports unavailable historical lineage honestly with current provenance', async () => {
    mockLineage(LINEAGE_UNAVAILABLE);
    render(<LineagePage />);
    await waitFor(() =>
      expect(screen.getByText('Historical lineage is unavailable.')).toBeInTheDocument(),
    );
    expect(
      screen.getByText(
        'No valid successful snapshots found; cannot establish historical-analysis lineage.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('lucknow_cafes.csv')).toBeInTheDocument();
    expect(screen.getByText('OpenStreetMap')).toBeInTheDocument();
  });

  it('renders the recorded snapshot timeline when lineage exists', async () => {
    mockLineage(LINEAGE_AVAILABLE);
    render(<LineagePage />);
    await waitFor(() =>
      expect(screen.getAllByText('2026-01-01T000000Z').length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText('2026-02-01T000000Z').length).toBeGreaterThan(0);
    expect(screen.getByText(/2 snapshots analyzed/)).toBeInTheDocument();
  });

  it('shows an error state with retry', async () => {
    mockLineage({}, false, 500);
    render(<LineagePage />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    mockLineage(LINEAGE_UNAVAILABLE);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() =>
      expect(screen.getByText('Historical lineage is unavailable.')).toBeInTheDocument(),
    );
  });
});

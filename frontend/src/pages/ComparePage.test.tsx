import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ComparePage } from './ComparePage.tsx';

const COMPARISON = {
  baseline: '2026-01-01T000000Z',
  target: '2026-02-01T000000Z',
  old_record_count: 2,
  new_record_count: 2,
  added: [{ osm_id: 'node3', name: 'Cafe Three' }],
  removed: [{ osm_id: 'node1', name: 'Cafe One' }],
  modified: [
    {
      osm_id: 'node2',
      name: 'Cafe Two Updated',
      changes: [{ field: 'name', old: 'Cafe Two', new: 'Cafe Two Updated' }],
    },
  ],
  unchanged: [],
  field_changes: [{ field: 'name', old: 'Cafe Two', new: 'Cafe Two Updated' }],
};

const HISTORY_TWO = {
  snapshots: [
    {
      snapshot_id: '2026-02-01T000000Z', retrieved_at_utc: '2026-02-01T00:00:00Z',
      source: 'OpenStreetMap', retrieval_method: 'Overpass API', endpoint: 'https://x',
      query: '[out:json];', record_count: 2, raw_file: 'raw.json',
      processed_file: 'cafes.csv', status: 'success',
    },
  ],
  summary: { snapshots_analyzed: 1 },
};

function mockCompare(comparisonBody: unknown, historyBody: unknown = HISTORY_TWO, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      const body = path.includes('/api/history/compare') ? comparisonBody : historyBody;
      return Promise.resolve({ ok, status, json: () => Promise.resolve(body) });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('ComparePage', () => {
  it('explains the requirement when snapshots are not selected', async () => {
    mockCompare(COMPARISON);
    render(<ComparePage baseline={null} target={null} />);
    await waitFor(() =>
      expect(
        screen.getByText('Snapshot comparison requires two available snapshots.'),
      ).toBeInTheDocument(),
    );
  });

  it('renders backend-computed added, removed, and modified records', async () => {
    mockCompare(COMPARISON);
    render(<ComparePage baseline="2026-01-01T000000Z" target="2026-02-01T000000Z" />);
    await waitFor(() => expect(screen.getByText('Added records')).toBeInTheDocument());
    expect(screen.getByText('Cafe Three')).toBeInTheDocument();
    expect(screen.getByText('Cafe One')).toBeInTheDocument();
    expect(screen.getByText(/name: Cafe Two → Cafe Two Updated/)).toBeInTheDocument();
  });

  it('shows an error state naming the backend problem', async () => {
    mockCompare({ detail: 'Unknown snapshot: a' }, HISTORY_TWO, false, 404);
    render(<ComparePage baseline="a" target="b" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText('Unknown snapshot: a')).toBeInTheDocument();
    mockCompare(COMPARISON);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => expect(screen.getByText('Added records')).toBeInTheDocument());
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { HistoryPage } from './HistoryPage.tsx';

const SNAP_A = {
  snapshot_id: '2026-01-01T000000Z', retrieved_at_utc: '2026-01-01T00:00:00Z',
  source: 'OpenStreetMap', retrieval_method: 'Overpass API',
  endpoint: 'https://overpass-api.de/api/interpreter', query: '[out:json];',
  record_count: 2, raw_file: 'raw.json', processed_file: 'cafes.csv', status: 'success',
};

const SNAP_B = {
  ...SNAP_A, snapshot_id: '2026-02-01T000000Z', retrieved_at_utc: '2026-02-01T00:00:00Z',
};

const HISTORY_EMPTY = {
  snapshots: [],
  summary: {
    snapshots_analyzed: 0, snapshot_ids: [], first_snapshot: null, latest_snapshot: null,
    unique_cafes: 0, added: 0, no_longer_observed: 0, modified: 0, unchanged: 0,
    field_summary: [], total_field_changes: 0,
  },
};

const HISTORY_TWO = {
  snapshots: [SNAP_B, SNAP_A],
  summary: {
    snapshots_analyzed: 2, snapshot_ids: [SNAP_A.snapshot_id, SNAP_B.snapshot_id],
    first_snapshot: SNAP_A.snapshot_id, latest_snapshot: SNAP_B.snapshot_id,
    unique_cafes: 3, added: 1, no_longer_observed: 1, modified: 1, unchanged: 0,
    field_summary: [['name', 1]], total_field_changes: 1,
  },
};

const DETAIL_B = {
  metadata: SNAP_B,
  integrity_status: 'PASSED',
  integrity_errors: [],
};

function mockHistory(historyBody: unknown, detailBody: unknown = DETAIL_B, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      const path = String(url);
      const body = path.includes('/api/history/') ? detailBody : historyBody;
      return Promise.resolve({ ok, status, json: () => Promise.resolve(body) });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('HistoryPage', () => {
  it('shows a loading state first', () => {
    mockHistory(HISTORY_EMPTY);
    render(<HistoryPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows an honest empty state when no snapshots exist', async () => {
    mockHistory(HISTORY_EMPTY);
    render(<HistoryPage />);
    await waitFor(() =>
      expect(
        screen.getByText('No historical snapshots are currently available.'),
      ).toBeInTheDocument(),
    );
  });

  it('lists snapshots newest-first with summary counts', async () => {
    mockHistory(HISTORY_TWO);
    render(<HistoryPage />);
    await waitFor(() =>
      expect(screen.getAllByText('2026-02-01T000000Z').length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText('2026-01-01T000000Z').length).toBeGreaterThan(0);
    expect(screen.getByText('Unique cafes observed')).toBeInTheDocument();
  });

  it('loads snapshot details on selection', async () => {
    mockHistory(HISTORY_TWO);
    render(<HistoryPage />);
    await waitFor(() =>
      expect(screen.getAllByText('2026-02-01T000000Z').length).toBeGreaterThan(0),
    );
    fireEvent.click(screen.getAllByRole('button', { name: 'View details' })[0]);
    await waitFor(() => expect(screen.getByText('Retrieval method')).toBeInTheDocument());
    expect(screen.getByText('PASSED')).toBeInTheDocument();
  });

  it('explains that comparison needs two snapshots when only one exists', async () => {
    mockHistory({ ...HISTORY_TWO, snapshots: [SNAP_A] });
    render(<HistoryPage />);
    await waitFor(() =>
      expect(
        screen.getByText('Snapshot comparison requires two available snapshots.'),
      ).toBeInTheDocument(),
    );
  });

  it('offers a comparison link once two different snapshots are chosen', async () => {
    mockHistory(HISTORY_TWO);
    render(<HistoryPage />);
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Compare snapshots' })).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText('Baseline snapshot'), {
      target: { value: SNAP_A.snapshot_id },
    });
    fireEvent.change(screen.getByLabelText('Target snapshot'), {
      target: { value: SNAP_B.snapshot_id },
    });
    const link = screen.getByRole('link', { name: 'Compare snapshots' });
    expect(link.getAttribute('href')).toContain('baseline=2026-01-01T000000Z');
    expect(link.getAttribute('href')).toContain('target=2026-02-01T000000Z');
  });

  it('shows an error state with retry', async () => {
    mockHistory({}, {}, false, 500);
    render(<HistoryPage />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    mockHistory(HISTORY_EMPTY);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() =>
      expect(
        screen.getByText('No historical snapshots are currently available.'),
      ).toBeInTheDocument(),
    );
  });
});

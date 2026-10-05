import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QualityPage } from './QualityPage.tsx';

const QUALITY = {
  report: {
    total_records: 33,
    valid_coordinate_records: 33,
    invalid_coordinate_records: 0,
    duplicate_osm_id_records: 0,
    duplicate_location_name_records: 0,
    field_completeness: {
      name: { present: 27, missing: 6, completeness_percentage: 81.8 },
      website: { present: 2, missing: 31, completeness_percentage: 6.1 },
    },
  },
  provenance: {
    source: 'OpenStreetMap',
    retrieval_method: 'Overpass API',
    retrieved_at: '2026-01-01T00:00:00+00:00',
    record_count: 33,
    source_file: 'data/processed/lucknow_cafes.csv',
  },
  records: [
    { osm_id: 'node1', quality_flags: ['missing_website'], quality_issue_count: 1 },
    { osm_id: 'node2', quality_flags: [], quality_issue_count: 0 },
  ],
};

function mockQuality(body: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({ ok, status, json: () => Promise.resolve(body) }),
    ),
  );
}

beforeEach(() => {
  mockQuality(QUALITY);
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('QualityPage', () => {
  it('shows a loading state first', () => {
    render(<QualityPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders overview totals from the report', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText('Dataset overview')).toBeInTheDocument());
    expect(screen.getByText('Valid coordinates')).toBeInTheDocument();
    expect(screen.getByText('Invalid coordinates')).toBeInTheDocument();
  });

  it('renders per-field present, missing, and percentage values', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText('81.8%')).toBeInTheDocument());
    expect(screen.getByRole('columnheader', { name: 'Present' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Missing' })).toBeInTheDocument();
    expect(screen.getByText('6.1%')).toBeInTheDocument();
  });

  it('reports zero duplicates honestly when there are none', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText('Duplicate findings')).toBeInTheDocument());
    expect(screen.getByText('No duplicate findings reported.')).toBeInTheDocument();
  });

  it('shows nonzero duplicate counts when reported', async () => {
    mockQuality({
      ...QUALITY,
      report: {
        ...QUALITY.report,
        duplicate_osm_id_records: 2,
        duplicate_location_name_records: 1,
      },
    });
    render(<QualityPage />);
    await waitFor(() => expect(screen.queryByText('No duplicate findings reported.')).not.toBeInTheDocument());
    expect(screen.getByText(/Duplicate OSM IDs: 2/)).toBeInTheDocument();
  });

  it('renders the per-record flags table', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText('node1')).toBeInTheDocument());
    expect(screen.getByText('missing_website')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'OSM ID' })).toBeInTheDocument();
  });

  it('shows provenance without server filesystem paths', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText(/Source: OpenStreetMap via Overpass API/)).toBeInTheDocument());
    expect(screen.getByText(/lucknow_cafes\.csv/)).toBeInTheDocument();
    expect(screen.queryByText(/C:\\/)).not.toBeInTheDocument();
  });

  it('documents limitations', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText('Limitations')).toBeInTheDocument());
    expect(screen.getByText(/Absence of metadata does not prove/)).toBeInTheDocument();
  });

  it('never shows an aggregate quality score', async () => {
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText('Dataset overview')).toBeInTheDocument());
    expect(screen.queryByText(/overall/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/aggregate/i)).not.toBeInTheDocument();
  });

  it('shows an empty state for a zero-record dataset', async () => {
    mockQuality({
      report: {
        total_records: 0, valid_coordinate_records: 0, invalid_coordinate_records: 0,
        duplicate_osm_id_records: 0, duplicate_location_name_records: 0, field_completeness: {},
      },
      provenance: { ...QUALITY.provenance, record_count: 0 },
      records: [],
    });
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByText(/zero records/i)).toBeInTheDocument());
  });

  it('shows an error state with retry on API failure', async () => {
    mockQuality({}, false, 500);
    let calls = 0;
    vi.mocked(fetch).mockImplementation((() => {
      calls += 1;
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ detail: 'down' }) });
    }) as unknown as typeof fetch);
    render(<QualityPage />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => expect(calls).toBeGreaterThan(1));
  });
});

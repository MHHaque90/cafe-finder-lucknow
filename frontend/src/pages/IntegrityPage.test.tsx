import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { IntegrityPage } from './IntegrityPage.tsx';

const INTEGRITY_REAL = {
  snapshot_integrity: {
    snapshot_id: null,
    status: 'NO_SNAPSHOTS',
    checks: [],
    errors: ['No snapshot directories exist'],
  },
  schema: {
    valid: false,
    schema_version: 1,
    missing_columns: [],
    unexpected_columns: [],
    invalid_types: { name: 'name: missing' },
    column_order_valid: true,
  },
  artifact: {
    path: 'data/processed/lucknow_cafes.csv',
    exists: true,
    readable: true,
    sha256_actual: 'abc123',
    sha256_expected: null,
    sha_match: null,
    size_actual: 3037,
    size_expected: null,
    size_match: null,
    valid: true,
    error: null,
  },
};

const INTEGRITY_PASS = {
  snapshot_integrity: {
    snapshot_id: '2026-02-01T000000Z',
    status: 'PASSED',
    checks: [],
    errors: [],
  },
  schema: {
    valid: true,
    schema_version: 1,
    missing_columns: [],
    unexpected_columns: [],
    invalid_types: {},
    column_order_valid: true,
  },
  artifact: { ...INTEGRITY_REAL.artifact, valid: true },
};

function mockIntegrity(body: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok, status, json: () => Promise.resolve(body) })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('IntegrityPage', () => {
  it('shows a loading state first', () => {
    mockIntegrity(INTEGRITY_REAL);
    render(<IntegrityPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('labels snapshot integrity unavailable and schema failed without scores', async () => {
    mockIntegrity(INTEGRITY_REAL);
    render(<IntegrityPage />);
    await waitFor(() => expect(screen.getByText('Snapshot integrity')).toBeInTheDocument());
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('Fail')).toBeInTheDocument();
    expect(screen.getByText('No snapshot directories exist')).toBeInTheDocument();
    expect(screen.getByText('name: missing')).toBeInTheDocument();
    expect(screen.getByText('abc123')).toBeInTheDocument();
    expect(screen.queryByText(/98% integrity/)).not.toBeInTheDocument();
  });

  it('labels passing checks as Pass', async () => {
    mockIntegrity(INTEGRITY_PASS);
    render(<IntegrityPage />);
    await waitFor(() => expect(screen.getByText('Snapshot integrity')).toBeInTheDocument());
    expect(screen.getAllByText('Pass')).toHaveLength(3);
  });

  it('shows an error state with retry', async () => {
    mockIntegrity({}, false, 500);
    render(<IntegrityPage />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    mockIntegrity(INTEGRITY_REAL);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => expect(screen.getByText('Snapshot integrity')).toBeInTheDocument());
  });
});

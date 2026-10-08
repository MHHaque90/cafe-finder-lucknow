import { useEffect, useState } from 'react';
import { compareSnapshots, getHistory } from '../api/client.ts';
import type { ComparisonResponse, HistoryResponse } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { ErrorState, LoadingState } from '../components/StatusStates.tsx';

interface CompareState {
  status: 'loading' | 'ready' | 'error';
  comparison: ComparisonResponse | null;
  error: string | null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value === 'object' && value !== null) return value as Record<string, unknown>;
  return null;
}

function cellText(value: unknown): string {
  if (value === null || value === undefined) return 'Not recorded';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function changeList(entry: unknown): Array<Record<string, unknown>> {
  const record = asRecord(entry);
  const changes = record?.['changes'];
  return Array.isArray(changes) ? changes.map(asRecord).filter((c) => c !== null) : [];
}

interface ComparePageProps {
  baseline: string | null;
  target: string | null;
}

/**
 * Snapshot comparison rendered from GET /api/history/compare. The backend
 * computes added, removed, modified, and unchanged records; this page
 * only presents them. Without two selected snapshots it offers honest
 * selection guidance instead of fabricated results.
 */
export function ComparePage({ baseline, target }: ComparePageProps) {
  const [state, setState] = useState<CompareState>({
    status: baseline !== null && target !== null ? 'loading' : 'error',
    comparison: null,
    error: baseline !== null && target !== null ? null : 'Two snapshots are required.',
  });
  const [history, setHistory] = useState<HistoryResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (baseline === null || target === null) {
      getHistory()
        .then((loaded) => {
          if (cancelled) return;
          setHistory(loaded);
        })
        .catch(() => {
          if (cancelled) return;
          setHistory(null);
        });
      return () => {
        cancelled = true;
      };
    }
    setState({ status: 'loading', comparison: null, error: null });
    compareSnapshots(baseline, target)
      .then((comparison) => {
        if (cancelled) return;
        setState({ status: 'ready', comparison, error: null });
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        setState({
          status: 'error',
          comparison: null,
          error: failure instanceof Error ? failure.message : 'Unable to load comparison.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, [baseline, target]);

  const retry = () => {
    if (baseline === null || target === null) return;
    setState({ status: 'loading', comparison: null, error: null });
    compareSnapshots(baseline, target)
      .then((comparison) => {
        setState({ status: 'ready', comparison, error: null });
      })
      .catch((failure: unknown) => {
        setState({
          status: 'error',
          comparison: null,
          error:
            failure instanceof ApiRequestError ? failure.message : 'Unable to load comparison.',
        });
      });
  };

  if (state.status === 'loading') {
    return (
      <div aria-live="polite">
        <LoadingState />
      </div>
    );
  }

  if (state.status === 'error' && (baseline === null || target === null)) {
    return (
      <div>
        <h2>Compare snapshots</h2>
        <div className="status">
          <p>Snapshot comparison requires two available snapshots.</p>
          <p>
            Choose a baseline and a target on the{' '}
            <a href="#/history">History page</a>, or wait until the pipeline records
            snapshots.
          </p>
        </div>
        {history !== null && history.snapshots.length > 0 && (
          <section aria-label="Available snapshots">
            <h3>Available snapshots</h3>
            <ul>
              {history.snapshots.map((snapshot) => (
                <li key={snapshot.snapshot_id}>
                  <code className="hash">{snapshot.snapshot_id}</code> — {snapshot.record_count}{' '}
                  records
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div aria-live="polite">
        <ErrorState message={state.error ?? 'Unable to load comparison.'} onRetry={retry} />
      </div>
    );
  }

  if (state.comparison === null) {
    return (
      <div className="status">
        <p>Comparison information is unavailable.</p>
      </div>
    );
  }

  const { comparison } = state;

  return (
    <div>
      <h2>Compare snapshots</h2>
      <p className="muted">
        Baseline <code className="hash">{comparison.baseline}</code> against target{' '}
        <code className="hash">{comparison.target}</code>, as computed by the API.
      </p>

      <section aria-label="Comparison summary">
        <h3>Summary</h3>
        <div className="stats">
          <div className="stat">
            <p className="stat-value">{comparison.added.length}</p>
            <p className="stat-label">Added</p>
          </div>
          <div className="stat">
            <p className="stat-value">{comparison.removed.length}</p>
            <p className="stat-label">Removed</p>
          </div>
          <div className="stat">
            <p className="stat-value">{comparison.modified.length}</p>
            <p className="stat-label">Modified</p>
          </div>
          <div className="stat">
            <p className="stat-value">{comparison.unchanged.length}</p>
            <p className="stat-label">Unchanged</p>
          </div>
        </div>
        <p className="muted">
          Baseline held {comparison.old_record_count} records; the target holds{' '}
          {comparison.new_record_count} records.
        </p>
      </section>

      <section aria-label="Added records">
        <h3>Added records</h3>
        {comparison.added.length === 0 ? (
          <p>No records were added.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <caption className="visually-hidden">Records present only in the target snapshot</caption>
              <thead>
                <tr>
                  <th scope="col">OSM ID</th>
                  <th scope="col">Name</th>
                </tr>
              </thead>
              <tbody>
                {comparison.added.map((row, index) => (
                  <tr key={String(row['osm_id'] ?? index)}>
                    <th scope="row">{cellText(row['osm_id'])}</th>
                    <td>{cellText(row['name'])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-label="Removed records">
        <h3>Removed records</h3>
        {comparison.removed.length === 0 ? (
          <p>No records were removed.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <caption className="visually-hidden">Records present only in the baseline snapshot</caption>
              <thead>
                <tr>
                  <th scope="col">OSM ID</th>
                  <th scope="col">Name</th>
                </tr>
              </thead>
              <tbody>
                {comparison.removed.map((row, index) => (
                  <tr key={String(row['osm_id'] ?? index)}>
                    <th scope="row">{cellText(row['osm_id'])}</th>
                    <td>{cellText(row['name'])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-label="Modified records">
        <h3>Modified records</h3>
        {comparison.modified.length === 0 ? (
          <p>No records were modified.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <caption className="visually-hidden">
                Records with field-level changes between baseline and target
              </caption>
              <thead>
                <tr>
                  <th scope="col">OSM ID</th>
                  <th scope="col">Name</th>
                  <th scope="col">Field changes</th>
                </tr>
              </thead>
              <tbody>
                {comparison.modified.map((entry, index) => (
                  <tr key={String(asRecord(entry)?.['osm_id'] ?? index)}>
                    <th scope="row">{cellText(asRecord(entry)?.['osm_id'])}</th>
                    <td>{cellText(asRecord(entry)?.['name'])}</td>
                    <td>
                      <ul>
                        {changeList(entry).map((change, changeIndex) => (
                          <li key={`${String(change['field'])}-${changeIndex}`}>
                            {cellText(change['field'])}: {cellText(change['old'])} →{' '}
                            {cellText(change['new'])}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

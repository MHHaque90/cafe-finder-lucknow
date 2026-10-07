import { useEffect, useState } from 'react';
import { getHistory, getSnapshot } from '../api/client.ts';
import type { HistoryResponse, SnapshotDetail } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { ErrorState, LoadingState } from '../components/StatusStates.tsx';
import { compareHash } from '../routing.ts';

interface HistoryState {
  status: 'loading' | 'ready' | 'empty' | 'error';
  history: HistoryResponse | null;
  error: string | null;
}

interface DetailState {
  status: 'idle' | 'loading' | 'ready' | 'error';
  detail: SnapshotDetail | null;
  error: string | null;
}

/**
 * Snapshot history rendered from GET /api/history. Snapshot identity,
 * counts, and ordering all come from the backend; this page only
 * presents them and links to detail and comparison views.
 */
export function HistoryPage() {
  const [state, setState] = useState<HistoryState>({
    status: 'loading',
    history: null,
    error: null,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailState>({ status: 'idle', detail: null, error: null });
  const [baseline, setBaseline] = useState('');
  const [target, setTarget] = useState('');

  useEffect(() => {
    let cancelled = false;
    getHistory()
      .then((history) => {
        if (cancelled) return;
        if (history.snapshots.length === 0) {
          setState({ status: 'empty', history, error: null });
        } else {
          setState({ status: 'ready', history, error: null });
        }
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        setState({
          status: 'error',
          history: null,
          error: failure instanceof Error ? failure.message : 'Unable to load history.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setState({ status: 'loading', history: null, error: null });
    setSelectedId(null);
    setDetail({ status: 'idle', detail: null, error: null });
    getHistory()
      .then((history) => {
        if (history.snapshots.length === 0) {
          setState({ status: 'empty', history, error: null });
        } else {
          setState({ status: 'ready', history, error: null });
        }
      })
      .catch((failure: unknown) => {
        setState({
          status: 'error',
          history: null,
          error: failure instanceof ApiRequestError ? failure.message : 'Unable to load history.',
        });
      });
  };

  const selectSnapshot = (snapshotId: string) => {
    setSelectedId(snapshotId);
    setDetail({ status: 'loading', detail: null, error: null });
    getSnapshot(snapshotId)
      .then((snapshotDetail) => {
        setDetail({ status: 'ready', detail: snapshotDetail, error: null });
      })
      .catch((failure: unknown) => {
        setDetail({
          status: 'error',
          detail: null,
          error: failure instanceof Error ? failure.message : 'Unable to load snapshot.',
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

  if (state.status === 'error') {
    return (
      <div aria-live="polite">
        <ErrorState message={state.error ?? 'Unable to load history.'} onRetry={retry} />
      </div>
    );
  }

  if (state.status === 'empty' || state.history === null) {
    return (
      <div aria-live="polite">
        <h2>History</h2>
        <p className="muted">
          Recorded dataset snapshots, as reported by the API — nothing reconstructed here.
        </p>
        <div className="status">
          <p>No historical snapshots are currently available.</p>
          <p>
            Snapshots are created by the data pipeline when fresh data is retrieved. Until
            then there is no history to show, and none is invented.
          </p>
        </div>
      </div>
    );
  }

  const { history } = state;
  const summary = history.summary as Record<string, unknown>;
  const analyzed = typeof summary.snapshots_analyzed === 'number' ? summary.snapshots_analyzed : 0;
  const uniqueCafes = typeof summary.unique_cafes === 'number' ? summary.unique_cafes : 0;
  const totalChanges =
    typeof summary.total_field_changes === 'number' ? summary.total_field_changes : 0;

  return (
    <div aria-live="polite">
      <h2>History</h2>
      <p className="muted">
        Recorded dataset snapshots, as reported by the API — nothing reconstructed here.
      </p>

      <section aria-label="History summary">
        <h3>Summary</h3>
        <div className="stats">
          <div className="stat">
            <p className="stat-value">{analyzed}</p>
            <p className="stat-label">Snapshots analyzed</p>
          </div>
          <div className="stat">
            <p className="stat-value">{uniqueCafes}</p>
            <p className="stat-label">Unique cafes observed</p>
          </div>
          <div className="stat">
            <p className="stat-value">{totalChanges}</p>
            <p className="stat-label">Field changes recorded</p>
          </div>
        </div>
      </section>

      <section aria-label="Snapshots">
        <h3>Snapshots</h3>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Snapshot</th>
                <th scope="col">Retrieved</th>
                <th scope="col">Records</th>
                <th scope="col">Source</th>
                <th scope="col">Details</th>
              </tr>
            </thead>
            <tbody>
              {history.snapshots.map((snapshot) => (
                <tr key={snapshot.snapshot_id}>
                  <td>
                    <code className="hash">{snapshot.snapshot_id}</code>
                  </td>
                  <td>{snapshot.retrieved_at_utc}</td>
                  <td>{snapshot.record_count}</td>
                  <td>{snapshot.source}</td>
                  <td>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => selectSnapshot(snapshot.snapshot_id)}
                      aria-expanded={selectedId === snapshot.snapshot_id}
                    >
                      {selectedId === snapshot.snapshot_id ? 'Hide details' : 'View details'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {detail.status === 'loading' && selectedId !== null && (
          <div className="status" role="status" aria-label="Loading snapshot details">
            <p>Loading snapshot details…</p>
          </div>
        )}
        {detail.status === 'error' && (
          <div className="status status-error" role="alert">
            <p>Unable to load snapshot details.</p>
            <p>{detail.error}</p>
          </div>
        )}
        {detail.status === 'ready' && detail.detail !== null && (
          <section aria-label="Snapshot details">
            <h3>Snapshot details</h3>
            <div className="table-scroll">
              <table>
                <tbody>
                  <tr>
                    <th scope="row">Snapshot</th>
                    <td>
                      <code className="hash">{detail.detail.metadata.snapshot_id}</code>
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Retrieved</th>
                    <td>{detail.detail.metadata.retrieved_at_utc}</td>
                  </tr>
                  <tr>
                    <th scope="row">Records</th>
                    <td>{detail.detail.metadata.record_count}</td>
                  </tr>
                  <tr>
                    <th scope="row">Source</th>
                    <td>{detail.detail.metadata.source}</td>
                  </tr>
                  <tr>
                    <th scope="row">Retrieval method</th>
                    <td>{detail.detail.metadata.retrieval_method}</td>
                  </tr>
                  <tr>
                    <th scope="row">Endpoint</th>
                    <td>{detail.detail.metadata.endpoint}</td>
                  </tr>
                  <tr>
                    <th scope="row">Raw file</th>
                    <td>{detail.detail.metadata.raw_file}</td>
                  </tr>
                  <tr>
                    <th scope="row">Processed file</th>
                    <td>{detail.detail.metadata.processed_file}</td>
                  </tr>
                  <tr>
                    <th scope="row">Status</th>
                    <td>{detail.detail.metadata.status}</td>
                  </tr>
                  <tr>
                    <th scope="row">Integrity</th>
                    <td>
                      {detail.detail.integrity_status}
                      {detail.detail.integrity_errors.length > 0 && (
                        <ul>
                          {detail.detail.integrity_errors.map((error) => (
                            <li key={error}>{error}</li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        )}
      </section>

      <section aria-label="Compare snapshots">
        <h3>Compare snapshots</h3>
        {history.snapshots.length < 2 ? (
          <div className="status">
            <p>Snapshot comparison requires two available snapshots.</p>
            <p>Only {history.snapshots.length} snapshot is currently recorded.</p>
          </div>
        ) : (
          <>
            <p>Select a baseline and a target snapshot. The backend computes the comparison.</p>
            <div className="form-row">
              <div className="field">
                <label htmlFor="compare-baseline">Baseline snapshot</label>
                <select
                  id="compare-baseline"
                  value={baseline}
                  onChange={(event) => setBaseline(event.target.value)}
                >
                  <option value="">Select a snapshot</option>
                  {history.snapshots.map((snapshot) => (
                    <option key={snapshot.snapshot_id} value={snapshot.snapshot_id}>
                      {snapshot.snapshot_id}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="compare-target">Target snapshot</label>
                <select
                  id="compare-target"
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                >
                  <option value="">Select a snapshot</option>
                  {history.snapshots.map((snapshot) => (
                    <option key={snapshot.snapshot_id} value={snapshot.snapshot_id}>
                      {snapshot.snapshot_id}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                {baseline !== '' && target !== '' && baseline !== target ? (
                  <a className="button-secondary" href={compareHash(baseline, target)}>
                    Compare snapshots
                  </a>
                ) : (
                  <span className="muted">Choose two different snapshots to compare.</span>
                )}
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { getIntegrity } from '../api/client.ts';
import type { IntegrityResponse } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { ErrorState, LoadingState } from '../components/StatusStates.tsx';

interface IntegrityState {
  status: 'loading' | 'ready' | 'error';
  integrity: IntegrityResponse | null;
  error: string | null;
}

type BadgeTone = 'pass' | 'fail' | 'unavailable';

function snapshotBadge(status: string): { tone: BadgeTone; label: string } {
  if (status === 'PASSED') return { tone: 'pass', label: 'Pass' };
  if (status === 'INTEGRITY_FAILED' || status === 'QUARANTINED' || status === 'INCOMPLETE') {
    return { tone: 'fail', label: 'Fail' };
  }
  return { tone: 'unavailable', label: 'Unavailable' };
}

function snapshotExplanation(status: string): string {
  switch (status) {
    case 'PASSED':
      return 'The latest snapshot passed all recorded integrity checks.';
    case 'INTEGRITY_FAILED':
      return 'The latest snapshot failed one or more integrity checks. See the errors below.';
    case 'QUARANTINED':
      return 'The latest snapshot is quarantined and cannot be trusted.';
    case 'INCOMPLETE':
      return 'The latest snapshot is incomplete.';
    case 'NO_MANIFEST':
      return 'The latest snapshot carries no manifest, so integrity cannot be established.';
    case 'SNAPSHOT_NOT_FOUND':
      return 'The referenced snapshot was not found.';
    case 'NO_SNAPSHOTS':
      return 'No snapshots have been recorded yet, so there is nothing to verify.';
    case 'NO_VALID_SNAPSHOTS':
      return 'Snapshot directories exist, but none holds a valid successful snapshot.';
    default:
      return `The backend reported status ${status}.`;
  }
}

/**
 * Integrity results rendered from GET /api/integrity. Snapshot verdicts,
 * schema validation, and artifact checks all come from the backend; this
 * page labels them Pass, Fail, or Unavailable without inventing scores.
 */
export function IntegrityPage() {
  const [state, setState] = useState<IntegrityState>({
    status: 'loading',
    integrity: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    getIntegrity()
      .then((integrity) => {
        if (cancelled) return;
        setState({ status: 'ready', integrity, error: null });
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        setState({
          status: 'error',
          integrity: null,
          error: failure instanceof Error ? failure.message : 'Unable to load integrity.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setState({ status: 'loading', integrity: null, error: null });
    getIntegrity()
      .then((integrity) => {
        setState({ status: 'ready', integrity, error: null });
      })
      .catch((failure: unknown) => {
        setState({
          status: 'error',
          integrity: null,
          error: failure instanceof ApiRequestError ? failure.message : 'Unable to load integrity.',
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
        <ErrorState message={state.error ?? 'Unable to load integrity.'} onRetry={retry} />
      </div>
    );
  }

  if (state.integrity === null) {
    return (
      <div className="status" aria-live="polite">
        <p>Integrity information is unavailable.</p>
      </div>
    );
  }

  const { integrity } = state;
  const snapshot = snapshotBadge(integrity.snapshot_integrity.status);
  const schemaTone: BadgeTone = integrity.schema.valid ? 'pass' : 'fail';
  const artifactTone: BadgeTone = integrity.artifact.valid ? 'pass' : 'fail';
  const invalidEntries = Object.entries(integrity.schema.invalid_types);

  return (
    <div aria-live="polite">
      <h2>Integrity</h2>
      <p className="muted">
        Whether the recorded data passes the repository&apos;s own checks — nothing scored here.
      </p>

      <section aria-label="Snapshot integrity">
        <h3>
          Snapshot integrity{' '}
          <span className={`status-badge status-badge-${snapshot.tone}`}>{snapshot.label}</span>
        </h3>
        <p>{snapshotExplanation(integrity.snapshot_integrity.status)}</p>
        <p className="muted">Backend status: {integrity.snapshot_integrity.status}</p>
        {integrity.snapshot_integrity.snapshot_id !== null && (
          <p>
            Verified snapshot: <code className="hash">{integrity.snapshot_integrity.snapshot_id}</code>
          </p>
        )}
        {integrity.snapshot_integrity.errors.length > 0 && (
          <>
            <h4>Errors</h4>
            <ul>
              {integrity.snapshot_integrity.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section aria-label="Schema validation">
        <h3>
          Schema validation{' '}
          <span className={`status-badge status-badge-${schemaTone}`}>
            {integrity.schema.valid ? 'Pass' : 'Fail'}
          </span>
        </h3>
        <p>
          The dataset currently served by the API {integrity.schema.valid ? 'matches' : 'does not match'}{' '}
          schema version {integrity.schema.schema_version}. Column order is{' '}
          {integrity.schema.column_order_valid ? 'valid' : 'invalid'}.
        </p>
        {integrity.schema.missing_columns.length > 0 && (
          <>
            <h4>Missing columns</h4>
            <ul>
              {integrity.schema.missing_columns.map((column) => (
                <li key={column}>{column}</li>
              ))}
            </ul>
          </>
        )}
        {integrity.schema.unexpected_columns.length > 0 && (
          <>
            <h4>Unexpected columns</h4>
            <ul>
              {integrity.schema.unexpected_columns.map((column) => (
                <li key={column}>{column}</li>
              ))}
            </ul>
          </>
        )}
        {invalidEntries.length > 0 && (
          <>
            <h4>Invalid values</h4>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Field</th>
                    <th scope="col">Problem</th>
                  </tr>
                </thead>
                <tbody>
                  {invalidEntries.map(([field, problem]) => (
                    <tr key={field}>
                      <td>{field}</td>
                      <td>{problem}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section aria-label="Dataset artifact">
        <h3>
          Dataset artifact{' '}
          <span className={`status-badge status-badge-${artifactTone}`}>
            {integrity.artifact.valid ? 'Pass' : 'Fail'}
          </span>
        </h3>
        <p>
          The dataset file {integrity.artifact.exists ? 'exists' : 'is missing'} and{' '}
          {integrity.artifact.readable ? 'is readable' : 'cannot be read'}.
        </p>
        <div className="table-scroll">
          <table>
            <tbody>
              <tr>
                <th scope="row">Artifact</th>
                <td>{integrity.artifact.path}</td>
              </tr>
              <tr>
                <th scope="row">SHA-256</th>
                <td>
                  {integrity.artifact.sha256_actual !== null ? (
                    <code className="hash">{integrity.artifact.sha256_actual}</code>
                  ) : (
                    'Not recorded'
                  )}
                </td>
              </tr>
              <tr>
                <th scope="row">Size</th>
                <td>
                  {integrity.artifact.size_actual !== null
                    ? `${integrity.artifact.size_actual} bytes`
                    : 'Not recorded'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="muted">
          No expected checksum or size is recorded for the live dataset, so hash and size are
          reported — not judged.
        </p>
        {integrity.artifact.error !== null && (
          <>
            <h4>Error</h4>
            <p>{integrity.artifact.error}</p>
          </>
        )}
      </section>
    </div>
  );
}

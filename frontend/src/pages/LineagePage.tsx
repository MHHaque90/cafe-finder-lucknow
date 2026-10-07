import { useEffect, useState } from 'react';
import { getLineage, getQuality } from '../api/client.ts';
import type { LineageResponse, QualityResponse } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { ErrorState, LoadingState } from '../components/StatusStates.tsx';

interface LineageState {
  status: 'loading' | 'ready' | 'error';
  lineage: LineageResponse | null;
  quality: QualityResponse | null;
  error: string | null;
}

function fileName(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] ?? path;
}

/**
 * Data lineage rendered from GET /api/lineage (historical snapshots) and
 * GET /api/quality (current-dataset provenance). Only recorded
 * relationships are shown; nothing is inferred about pipeline stages.
 */
export function LineagePage() {
  const [state, setState] = useState<LineageState>({
    status: 'loading',
    lineage: null,
    quality: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getLineage(), getQuality()])
      .then(([lineage, quality]) => {
        if (cancelled) return;
        setState({ status: 'ready', lineage, quality, error: null });
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        setState({
          status: 'error',
          lineage: null,
          quality: null,
          error: failure instanceof Error ? failure.message : 'Unable to load lineage.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setState({ status: 'loading', lineage: null, quality: null, error: null });
    Promise.all([getLineage(), getQuality()])
      .then(([lineage, quality]) => {
        setState({ status: 'ready', lineage, quality, error: null });
      })
      .catch((failure: unknown) => {
        setState({
          status: 'error',
          lineage: null,
          quality: null,
          error: failure instanceof ApiRequestError ? failure.message : 'Unable to load lineage.',
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
        <ErrorState message={state.error ?? 'Unable to load lineage.'} onRetry={retry} />
      </div>
    );
  }

  if (state.lineage === null) {
    return (
      <div className="status" aria-live="polite">
        <p>Lineage information is not recorded for this dataset.</p>
      </div>
    );
  }

  const { lineage, quality } = state;
  const provenance = quality?.provenance ?? null;

  return (
    <div aria-live="polite">
      <h2>Lineage</h2>
      <p className="muted">
        Where the data came from and what is recorded about its path — nothing inferred.
      </p>

      <section aria-label="Historical lineage">
        <h3>Historical lineage</h3>
        {!lineage.available || lineage.report === null ? (
          <div className="status">
            <p>Historical lineage is unavailable.</p>
            {lineage.reason !== null && <p>{lineage.reason}</p>}
            <p>
              Snapshot-to-snapshot lineage can only be established once the pipeline records
              successful snapshots.
            </p>
          </div>
        ) : (
          <>
            <p>
              {lineage.report.snapshots_analyzed} snapshots analyzed, from{' '}
              <code className="hash">{lineage.report.first_snapshot.snapshot_id}</code> to{' '}
              <code className="hash">{lineage.report.latest_snapshot.snapshot_id}</code>.
            </p>
            <ol className="timeline">
              {lineage.report.snapshots.map((snapshot) => (
                <li key={snapshot.snapshot_id}>
                  <code className="hash">{snapshot.snapshot_id}</code>
                  <br />
                  Retrieved {snapshot.retrieved_at_utc} — {snapshot.record_count} records.
                </li>
              ))}
            </ol>
            <p className="muted">Lineage report generated {lineage.report.generated_at_utc}.</p>
          </>
        )}
      </section>

      <section aria-label="Current dataset provenance">
        <h3>Current dataset provenance</h3>
        {provenance === null ? (
          <div className="status">
            <p>Provenance for the current dataset is unavailable.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <tbody>
                <tr>
                  <th scope="row">Source</th>
                  <td>{provenance.source}</td>
                </tr>
                <tr>
                  <th scope="row">Retrieval method</th>
                  <td>{provenance.retrieval_method}</td>
                </tr>
                <tr>
                  <th scope="row">Retrieved</th>
                  <td>{provenance.retrieved_at}</td>
                </tr>
                <tr>
                  <th scope="row">Records</th>
                  <td>{provenance.record_count}</td>
                </tr>
                <tr>
                  <th scope="row">Source file</th>
                  <td>
                    {provenance.source_file !== null ? fileName(provenance.source_file) : 'Not recorded'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-label="Limitations">
        <h3>Limitations</h3>
        <ul>
          <li>Only recorded snapshot relationships are shown; pipeline stages are not inferred.</li>
          <li>Absence of historical lineage does not mean the current dataset is unreliable.</li>
          <li>
            Data: OpenStreetMap contributors (ODbL 1.0) via Overpass API.{' '}
            <a href="https://www.openstreetmap.org/copyright">Attribution</a>.
          </li>
        </ul>
      </section>
    </div>
  );
}

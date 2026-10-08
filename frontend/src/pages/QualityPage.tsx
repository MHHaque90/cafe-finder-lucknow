import { useEffect, useState } from 'react';
import { getQuality } from '../api/client.ts';
import type { QualityResponse } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { ErrorState, LoadingState } from '../components/StatusStates.tsx';

interface QualityState {
  status: 'loading' | 'ready' | 'empty' | 'error';
  quality: QualityResponse | null;
  error: string | null;
}

function sourceFileName(path: string | null): string | null {
  if (path === null || path === undefined || path === '') return null;
  const parts = path.split(/[\\/]/).filter((part) => part !== '');
  return parts.length > 0 ? parts[parts.length - 1] as string : null;
}

/**
 * Dataset reliability, read from GET /api/quality. Incomplete metadata is
 * expected source-data behavior and is never confused with application
 * failure. No aggregate score exists in the API and none is shown.
 */
export function QualityPage() {
  const [state, setState] = useState<QualityState>({
    status: 'loading',
    quality: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      getQuality()
        .then((quality) => {
          if (cancelled) return;
          const total = typeof quality.report.total_records === 'number'
            ? quality.report.total_records
            : quality.records.length;
          setState({
            status: total === 0 ? 'empty' : 'ready',
            quality,
            error: null,
          });
        })
        .catch((failure: unknown) => {
          if (cancelled) return;
          setState({
            status: 'error',
            quality: null,
            error: failure instanceof Error ? failure.message : 'Unable to load quality information.',
          });
        });
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setState({ status: 'loading', quality: null, error: null });
    getQuality()
      .then((quality) => {
        const total = typeof quality.report.total_records === 'number'
          ? quality.report.total_records
          : quality.records.length;
        setState({
          status: total === 0 ? 'empty' : 'ready',
          quality,
          error: null,
        });
      })
      .catch((failure: unknown) => {
        setState({
          status: 'error',
          quality: null,
          error: failure instanceof ApiRequestError ? failure.message : 'Unable to load quality information.',
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
        <ErrorState message={state.error ?? 'Unable to load quality information.'} onRetry={retry} />
      </div>
    );
  }

  if (state.status === 'empty' || state.quality === null) {
    return (
      <div className="status" aria-live="polite">
        <p>No quality information is available because the dataset currently holds zero records.</p>
      </div>
    );
  }

  const { quality } = state;
  const report = quality.report as Record<string, unknown>;
  const completeness = (report.field_completeness ?? {}) as Record<
    string,
    { present?: unknown; missing?: unknown; completeness_percentage?: unknown }
  >;
  const fileName = sourceFileName(
    typeof quality.provenance.source_file === 'string' ? quality.provenance.source_file : null,
  );

  return (
    <div>
      <h2>Data Quality</h2>
      <p className="muted">
        Reliability of the current dataset. Missing metadata is expected in
        OpenStreetMap source data — it is reported here, not treated as a failure.
      </p>

      <section aria-label="Dataset overview">
        <h3>Dataset overview</h3>
        <div className="stats">
          <div className="stat">
            <p className="stat-value">{String(report.total_records ?? '?')}</p>
            <p className="stat-label">Total records</p>
          </div>
          <div className="stat">
            <p className="stat-value">{String(report.valid_coordinate_records ?? '?')}</p>
            <p className="stat-label">Valid coordinates</p>
          </div>
          <div className="stat">
            <p className="stat-value">{String(report.invalid_coordinate_records ?? '?')}</p>
            <p className="stat-label">Invalid coordinates</p>
          </div>
          <div className="stat">
            <p className="stat-value">{String(report.duplicate_osm_id_records ?? '?')}</p>
            <p className="stat-label">Duplicate OSM IDs</p>
          </div>
          <div className="stat">
            <p className="stat-value">{String(report.duplicate_location_name_records ?? '?')}</p>
            <p className="stat-label">Duplicate locations</p>
          </div>
        </div>
      </section>

      <section aria-label="Field completeness">
        <h3>Field completeness</h3>
        <p>Present, missing, and percentage per canonical field.</p>
        <div className="table-scroll">
          <table>
            <caption className="visually-hidden">
              Present, missing, and completeness percentage per canonical field
            </caption>
            <thead>
              <tr>
                <th scope="col">Field</th>
                <th scope="col">Present</th>
                <th scope="col">Missing</th>
                <th scope="col">Complete</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(completeness).map(([field, metrics]) => (
                <tr key={field}>
                  <th scope="row">{field}</th>
                  <td>{String(metrics.present ?? '?')}</td>
                  <td>{String(metrics.missing ?? '?')}</td>
                  <td>
                    {typeof metrics.completeness_percentage === 'number'
                      ? `${metrics.completeness_percentage.toFixed(1)}%`
                      : '?'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-label="Coordinate validity">
        <h3>Coordinate validity</h3>
        <p>
          {String(report.valid_coordinate_records ?? '?')} records carry valid coordinates;{' '}
          {String(report.invalid_coordinate_records ?? '?')} do not. Validity is decided by
          the backend checks, not by whether a point renders on a map.
        </p>
      </section>

      <section aria-label="Duplicate findings">
        <h3>Duplicate findings</h3>
        {Number(report.duplicate_osm_id_records ?? 0) === 0 &&
        Number(report.duplicate_location_name_records ?? 0) === 0 ? (
          <p>No duplicate findings reported.</p>
        ) : (
          <p>
            Duplicate OSM IDs: {String(report.duplicate_osm_id_records ?? '?')}; duplicate
            locations: {String(report.duplicate_location_name_records ?? '?')}.
          </p>
        )}
      </section>

      <section aria-label="Record-level flags">
        <h3>Record-level flags</h3>
        <p>Per-record issues. An empty flag list means a clean record.</p>
        <div className="table-scroll">
          <table>
            <caption className="visually-hidden">
              Per-record quality issues by OSM identifier
            </caption>
            <thead>
              <tr>
                <th scope="col">OSM ID</th>
                <th scope="col">Flags</th>
                <th scope="col">Issues</th>
              </tr>
            </thead>
            <tbody>
              {quality.records.map((record) => (
                <tr key={record.osm_id ?? 'unknown'}>
                  <th scope="row">{record.osm_id ?? 'unknown'}</th>
                  <td>{record.quality_flags.length > 0 ? record.quality_flags.join(', ') : '—'}</td>
                  <td>{record.quality_issue_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-label="Provenance">
        <h3>Provenance</h3>
        <p>
          Source: {quality.provenance.source} via {quality.provenance.retrieval_method}.
          Retrieved {quality.provenance.retrieved_at}; {quality.provenance.record_count} records
          {fileName !== null ? ` from ${fileName}` : ''}. OSM-derived data is ODbL licensed —{' '}
          <a href="https://www.openstreetmap.org/copyright">attribution</a>.
        </p>
      </section>

      <section aria-label="Limitations">
        <h3>Limitations</h3>
        <ul>
          <li>OpenStreetMap metadata completeness varies; some cafes lack websites, phone numbers, or opening hours.</li>
          <li>The dataset covers Lucknow records retrieved through Overpass; it is not a census of all Lucknow cafes.</li>
          <li>Data refresh is operator-controlled; freshness reflects the last retrieval.</li>
          <li>Absence of metadata does not prove absence of the underlying real-world information.</li>
        </ul>
      </section>
    </div>
  );
}

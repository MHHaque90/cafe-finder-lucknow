import { useEffect, useState } from 'react';
import { getAnalytics, getCafes } from '../api/client.ts';
import type { AnalyticsResponse, CafeResult } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { CafeMap } from '../components/CafeMap.tsx';
import { ErrorState, LoadingState } from '../components/StatusStates.tsx';

interface AnalyticsState {
  status: 'loading' | 'ready' | 'empty' | 'error';
  analytics: AnalyticsResponse | null;
  cafes: CafeResult[];
  error: string | null;
}

/**
 * Dataset analytics rendered from GET /api/analytics (plus cafe records
 * for the read-only location map). All numbers come from the API;
 * bars and tables only present them.
 */
export function AnalyticsPage() {
  const [state, setState] = useState<AnalyticsState>({
    status: 'loading',
    analytics: null,
    cafes: [],
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getAnalytics(), getCafes({})])
      .then(([analytics, cafes]) => {
        if (cancelled) return;
        if (analytics.overview.total_records === 0) {
          setState({ status: 'empty', analytics, cafes: [], error: null });
        } else {
          setState({ status: 'ready', analytics, cafes: cafes.results, error: null });
        }
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        setState({
          status: 'error',
          analytics: null,
          cafes: [],
          error: failure instanceof Error ? failure.message : 'Unable to load analytics.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setState({ status: 'loading', analytics: null, cafes: [], error: null });
    Promise.all([getAnalytics(), getCafes({})])
      .then(([analytics, cafes]) => {
        if (analytics.overview.total_records === 0) {
          setState({ status: 'empty', analytics, cafes: [], error: null });
        } else {
          setState({ status: 'ready', analytics, cafes: cafes.results, error: null });
        }
      })
      .catch((failure: unknown) => {
        setState({
          status: 'error',
          analytics: null,
          cafes: [],
          error: failure instanceof ApiRequestError ? failure.message : 'Unable to load analytics.',
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
        <ErrorState message={state.error ?? 'Unable to load analytics.'} onRetry={retry} />
      </div>
    );
  }

  if (state.status === 'empty' || state.analytics === null) {
    return (
      <div className="status" aria-live="polite">
        <p>No analytics are available because the dataset currently holds zero records.</p>
      </div>
    );
  }

  const { analytics, cafes } = state;
  const maxCuisine = Math.max(1, ...analytics.cuisine.map((entry) => entry.count));
  const bounds = analytics.coordinates.bounds;

  return (
    <div aria-live="polite">
      <h2>Analytics</h2>
      <p className="muted">Lucknow cafe dataset, as reported by the API — nothing computed here.</p>

      <section aria-label="Overview">
        <h3>Overview</h3>
        <div className="stats">
          <div className="stat">
            <p className="stat-value">{analytics.overview.total_records}</p>
            <p className="stat-label">Total cafes</p>
          </div>
          <div className="stat">
            <p className="stat-value">{analytics.overview.columns.length}</p>
            <p className="stat-label">Data columns</p>
          </div>
          <div className="stat">
            <p className="stat-value">{analytics.coordinates.count}</p>
            <p className="stat-label">Records with valid coordinates</p>
          </div>
        </div>
      </section>

      <section aria-label="Cuisine distribution">
        <h3>Cuisine distribution</h3>
        <p>Cuisine tags recorded in the current dataset, most common first.</p>
        <div className="bars" role="img" aria-label={`Bar chart of cuisine tags. Top tag: ${analytics.cuisine[0]?.tag ?? 'none'}.`}>
          {analytics.cuisine.map((entry) => (
            <div className="bar-row" key={entry.tag}>
              <span className="bar-label">{entry.tag}</span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${(entry.count / maxCuisine) * 100}%` }} />
              </span>
              <span className="bar-value">{entry.count}</span>
            </div>
          ))}
        </div>
        <details>
          <summary>Data table</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Cuisine tag</th>
                  <th scope="col">Records</th>
                </tr>
              </thead>
              <tbody>
                {analytics.cuisine.map((entry) => (
                  <tr key={entry.tag}>
                    <td>{entry.tag}</td>
                    <td>{entry.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section aria-label="Data completeness">
        <h3>Data completeness</h3>
        <p>Percentage of records containing each field. Gaps are reported, not filled.</p>
        <div className="bars" role="img" aria-label="Bar chart of per-field completeness percentages.">
          {Object.entries(analytics.completeness).map(([field, percent]) => (
            <div className="bar-row" key={field}>
              <span className="bar-label">{field}</span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${percent}%` }} />
              </span>
              <span className="bar-value">{percent.toFixed(1)}%</span>
            </div>
          ))}
        </div>
        <details>
          <summary>Data table</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Field</th>
                  <th scope="col">Completeness</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(analytics.completeness).map(([field, percent]) => (
                  <tr key={field}>
                    <td>{field}</td>
                    <td>{percent.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <section aria-label="Geographic distribution">
        <h3>Geographic distribution</h3>
        <p>
          {analytics.coordinates.count} of {analytics.overview.total_records} records carry
          usable coordinates{bounds !== null && (
            <>
              {' '}spanning {bounds.min_latitude.toFixed(4)}–{bounds.max_latitude.toFixed(4)} latitude
              and {bounds.min_longitude.toFixed(4)}–{bounds.max_longitude.toFixed(4)} longitude
            </>
          )}
          . Positions reflect OpenStreetMap coverage, not official city boundaries.
        </p>
        <CafeMap
          cafes={cafes}
          selectedOsmId={null}
          onSelect={() => undefined}
          center={null}
          radiusKm={null}
          notice={cafes.length === 0 ? 'No mapped locations to show.' : null}
        />
      </section>
    </div>
  );
}

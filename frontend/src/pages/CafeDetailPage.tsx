import { useEffect, useState } from 'react';
import { getCafe, getQuality } from '../api/client.ts';
import type { CafeResult, QualityProvenance, QualityRecordFlags } from '../api/types.ts';
import { ApiRequestError } from '../api/types.ts';
import { Field } from '../components/CafeCard.tsx';
import { CafeMap } from '../components/CafeMap.tsx';
import { ScoreBreakdown } from '../components/ScoreBreakdown.tsx';

/**
 * Single-cafe detail view. Loads the authoritative record from
 * GET /api/cafes/{osm_id} (never from navigation state) plus the
 * record's quality flags from GET /api/quality. When the Discover query
 * string carries a cuisine filter, it is forwarded so ranking fields
 * come from the same Python scorer as search results.
 */
export function CafeDetailPage({ osmId }: { osmId: string }) {
  const [cafe, setCafe] = useState<CafeResult | null>(null);
  const [flags, setFlags] = useState<QualityRecordFlags | null>(null);
  const [provenance, setProvenance] = useState<QualityProvenance | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'not-found' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setCafe(null);
    const cuisine = new URLSearchParams(window.location.search).get('cuisine') ?? undefined;
    Promise.all([getCafe(osmId, cuisine), getQuality()])
      .then(([record, quality]) => {
        if (cancelled) return;
        setCafe(record);
        setFlags(quality.records.find((entry) => entry.osm_id === record.osm_id) ?? null);
        setProvenance(quality.provenance);
        setStatus('ready');
      })
      .catch((failure: unknown) => {
        if (cancelled) return;
        if (failure instanceof ApiRequestError && failure.status === 404) {
          setStatus('not-found');
        } else {
          setStatus('error');
          setError(failure instanceof Error ? failure.message : 'Unable to load this cafe.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [osmId]);

  if (status === 'loading') {
    return (
      <div className="status" role="status" aria-label="Loading cafe details">
        <div className="skeleton" aria-hidden="true">
          <div className="skeleton-line" />
          <div className="skeleton-line skeleton-line-short" />
        </div>
        <p>Loading cafe details…</p>
      </div>
    );
  }

  if (status === 'not-found') {
    return (
      <div className="status" role="alert">
        <p>No cafe found for this ID.</p>
        <p>
          <a href="#/">← Back to results</a>
        </p>
      </div>
    );
  }

  if (status === 'error' || cafe === null) {
    return (
      <div className="status status-error" role="alert">
        <p>Unable to load this cafe.</p>
        {error !== '' && <p>{error}</p>}
        <p>
          <a href="#/">← Back to results</a>
        </p>
      </div>
    );
  }

  const address = [cafe.street, cafe.housenumber, cafe.city, cafe.postcode]
    .filter((part): part is string => part !== null && part !== undefined && part !== '')
    .join(', ');
  const coordinates =
    cafe.latitude !== null && cafe.longitude !== null
      ? `${cafe.latitude.toFixed(6)}, ${cafe.longitude.toFixed(6)}`
      : null;

  return (
    <article className="detail">
      <p>
        <a href="#/">← Back to results</a>
      </p>
      <h2>{cafe.name ?? 'Name unavailable in dataset'}</h2>
      <p className="muted">Record {cafe.osm_id}</p>

      <section aria-label="Location">
        <h3>Location</h3>
        {address !== '' ? (
          <p>{address}</p>
        ) : (
          <p className="card-row-missing">Address unavailable in dataset</p>
        )}
        {coordinates !== null ? (
          <p>
            Coordinates: {coordinates} (straight-line positions, not walking distances)
          </p>
        ) : (
          <p className="card-row-missing">Coordinates unavailable in dataset</p>
        )}
      </section>

      {cafe.score_total !== null && cafe.score_total !== undefined && (
        <section aria-label="Ranking">
          <h3>Ranking</h3>
          <ScoreBreakdown cafe={cafe} />
        </section>
      )}

      <section aria-label="Cafe information">
        <h3>Cafe information</h3>
        <Field label="Cuisine" value={cafe.cuisine} unavailable="Cuisine unavailable in dataset" />
        {cafe.website ? (
          <p>
            Website: <a href={cafe.website} target="_blank" rel="noopener noreferrer">{cafe.website}</a>
          </p>
        ) : (
          <p className="card-row-missing">Website unavailable in dataset</p>
        )}
        <Field label="Phone" value={cafe.phone} unavailable="Phone unavailable in dataset" />
        <Field
          label="Opening hours"
          value={cafe.opening_hours}
          unavailable="Opening hours unavailable in dataset"
        />
      </section>

      <section aria-label="Data quality for this record">
        <h3>Data quality for this record</h3>
        {flags === null || flags.quality_flags.length === 0 ? (
          <p>No quality issues flagged for this record.</p>
        ) : (
          <ul>
            {flags.quality_flags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        )}
      </section>

      {provenance !== null && (
        <section aria-label="Provenance">
          <h3>Provenance</h3>
          <p>
            Source: {provenance.source} via {provenance.retrieval_method}. OSM-derived data is
            ODbL licensed — <a href="https://www.openstreetmap.org/copyright">attribution</a>.
          </p>
        </section>
      )}

      <section aria-label="Map">
        <h3>Map</h3>
        <CafeMap
          cafes={[cafe]}
          selectedOsmId={cafe.osm_id}
          onSelect={() => undefined}
          center={null}
          radiusKm={null}
          notice={cafe.latitude === null || cafe.longitude === null ? 'No mapped location is available for this cafe.' : null}
          interactiveMarkers={false}
        />
      </section>
    </article>
  );
}

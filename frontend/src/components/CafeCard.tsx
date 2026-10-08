import type { CafeResult } from '../api/types.ts';
import { detailHash } from '../routing.ts';
import { ScoreBreakdown } from './ScoreBreakdown.tsx';

function addressOf(cafe: CafeResult): string | null {
  const parts = [cafe.street, cafe.housenumber, cafe.city, cafe.postcode].filter(
    (part): part is string => part !== null && part !== undefined && part !== '',
  );
  return parts.length > 0 ? parts.join(', ') : null;
}

export function Field({ label, value, unavailable }: { label: string; value: string | null; unavailable: string }) {
  if (value === null || value === undefined || value === '') {
    return (
      <p className="card-row card-row-missing">
        <span className="card-label">{label}:</span> {unavailable}
      </p>
    );
  }
  return (
    <p className="card-row">
      <span className="card-label">{label}:</span> {value}
    </p>
  );
}

interface CafeCardProps {
  cafe: CafeResult;
  /** Optional map-highlight toggle. Provided only by list views where the
   *  card click itself is mouse-only; a native button keeps the same
   *  action keyboard- and screen-reader-operable. */
  highlightLabel?: string;
  highlightPressed?: boolean;
  onHighlight?: () => void;
}

/**
 * One cafe result card. Renders only API data; every missing field gets
 * an explicit "unavailable in dataset" label instead of a placeholder.
 */
export function CafeCard({ cafe, highlightLabel, highlightPressed, onHighlight }: CafeCardProps) {
  const address = addressOf(cafe);
  return (
    <article className="card" aria-labelledby={`cafe-${cafe.osm_id}`}>
      <h3 id={`cafe-${cafe.osm_id}`}>{cafe.name ?? 'Name unavailable in dataset'}</h3>
      <Field label="Cuisine" value={cafe.cuisine} unavailable="Cuisine unavailable in dataset" />
      {address !== null ? (
        <p className="card-row">
          <span className="card-label">Address:</span> {address}
        </p>
      ) : (
        <p className="card-row card-row-missing">
          <span className="card-label">Address:</span> Address unavailable in dataset
        </p>
      )}
      {cafe.distance_km !== null && cafe.distance_km !== undefined && (
        <p className="card-row">
          <span className="card-label">Distance:</span> {cafe.distance_km.toFixed(2)} km
        </p>
      )}
      {cafe.website ? (
        <p className="card-row">
          <span className="card-label">Website:</span>{' '}
          <a href={cafe.website} target="_blank" rel="noreferrer">
            {cafe.website}
          </a>
        </p>
      ) : (
        <p className="card-row card-row-missing">
          <span className="card-label">Website:</span> Website unavailable in dataset
        </p>
      )}
      <Field label="Phone" value={cafe.phone} unavailable="Phone unavailable in dataset" />
      <Field
        label="Opening hours"
        value={cafe.opening_hours}
        unavailable="Opening hours unavailable in dataset"
      />
      <ScoreBreakdown cafe={cafe} />
      <p className="card-row">
        <a href={detailHash(cafe.osm_id)}>View details</a>
        {onHighlight !== undefined && highlightLabel !== undefined && (
          <>
            {' · '}
            <button
              type="button"
              className="link-button"
              aria-pressed={highlightPressed ?? false}
              onClick={(event) => {
                // The surrounding card also selects on click; the button
                // must not double-trigger it when toggling off.
                event.stopPropagation();
                onHighlight();
              }}
            >
              {highlightLabel}
            </button>
          </>
        )}
      </p>
    </article>
  );
}

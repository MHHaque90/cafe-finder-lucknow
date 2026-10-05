import type { CafeResult } from '../api/types.ts';

/** Renders one scored component line (points only, no denominators). */
function ScoreLine({ label, points }: { label: string; points: number | null }) {
  if (points === null || points === undefined) return null;
  return (
    <li>
      {label}: {points} pts
    </li>
  );
}

interface ScoreBreakdownProps {
  cafe: CafeResult;
}

/**
 * Renders the ranking values returned by the API exactly as received:
 * the total followed by the per-component points and the verbatim
 * `reasons` strings. No scoring mathematics lives here.
 */
export function ScoreBreakdown({ cafe }: ScoreBreakdownProps) {
  if (cafe.score_total === null || cafe.score_total === undefined) return null;
  return (
    <div className="score">
      <p className="score-total">
        Score: {cafe.score_total}/100
      </p>
      <ul className="score-parts">
        <ScoreLine label="Distance" points={cafe.score_distance} />
        <ScoreLine label="Cuisine" points={cafe.score_cuisine} />
        <ScoreLine label="Opening hours" points={cafe.score_opening_hours} />
        <ScoreLine label="Website" points={cafe.score_website} />
        <ScoreLine label="Phone" points={cafe.score_phone} />
      </ul>
      {cafe.score_reasons !== null && cafe.score_reasons !== undefined && cafe.score_reasons.length > 0 && (
        <div className="score-reasons">
          <p className="score-reasons-title">Why:</p>
          <ul>
            {cafe.score_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

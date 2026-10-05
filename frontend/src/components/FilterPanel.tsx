import { CUISINE_OPTIONS } from '../api/client.ts';

interface FilterPanelProps {
  cuisine: string;
  hasWebsite: boolean;
  hasPhone: boolean;
  hasHours: boolean;
  lat: string;
  lon: string;
  radius: string;
  onCuisineChange: (value: string) => void;
  onHasWebsiteChange: (value: boolean) => void;
  onHasPhoneChange: (value: boolean) => void;
  onHasHoursChange: (value: boolean) => void;
  onLatChange: (value: string) => void;
  onLonChange: (value: string) => void;
  onRadiusChange: (value: string) => void;
  onClear: () => void;
}

export function FilterPanel(props: FilterPanelProps) {
  const {
    cuisine, hasWebsite, hasPhone, hasHours, lat, lon, radius,
    onCuisineChange, onHasWebsiteChange, onHasPhoneChange, onHasHoursChange,
    onLatChange, onLonChange, onRadiusChange, onClear,
  } = props;
  return (
    <div className="filter-panel">
      <div className="field">
        <label htmlFor="cuisine-filter">Cuisine</label>
        <select id="cuisine-filter" value={cuisine} onChange={(event) => onCuisineChange(event.target.value)}>
          <option value="">All cuisines</option>
          {CUISINE_OPTIONS.map((tag) => (
            <option key={tag} value={tag}>
              {tag}
            </option>
          ))}
        </select>
        <p className="hint">Exact tag match, same as the API.</p>
      </div>
      <fieldset className="field">
        <legend>Must have</legend>
        <label className="check">
          <input type="checkbox" checked={hasWebsite} onChange={(event) => onHasWebsiteChange(event.target.checked)} />
          Website
        </label>
        <label className="check">
          <input type="checkbox" checked={hasPhone} onChange={(event) => onHasPhoneChange(event.target.checked)} />
          Phone
        </label>
        <label className="check">
          <input type="checkbox" checked={hasHours} onChange={(event) => onHasHoursChange(event.target.checked)} />
          Opening hours
        </label>
        <p className="hint">Filters combine with AND logic.</p>
      </fieldset>
      <fieldset className="field">
        <legend>Location</legend>
        <label htmlFor="lat-input">Latitude</label>
        <input
          id="lat-input"
          type="number"
          inputMode="decimal"
          step="any"
          min={-90}
          max={90}
          placeholder="26.8467"
          value={lat}
          onChange={(event) => onLatChange(event.target.value)}
        />
        <label htmlFor="lon-input">Longitude</label>
        <input
          id="lon-input"
          type="number"
          inputMode="decimal"
          step="any"
          min={-180}
          max={180}
          placeholder="80.9462"
          value={lon}
          onChange={(event) => onLonChange(event.target.value)}
        />
        <label htmlFor="radius-input">Radius (km)</label>
        <input
          id="radius-input"
          type="number"
          inputMode="decimal"
          step="any"
          min={0}
          placeholder="3"
          value={radius}
          onChange={(event) => onRadiusChange(event.target.value)}
        />
        <p className="hint">Radius needs both latitude and longitude.</p>
      </fieldset>
      <button type="button" className="button-secondary" onClick={onClear}>
        Clear filters
      </button>
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { CafeCard } from '../components/CafeCard.tsx';
import { CafeMap } from '../components/CafeMap.tsx';
import { EmptyState, ErrorState, LoadingState } from '../components/StatusStates.tsx';
import { FilterPanel } from '../components/FilterPanel.tsx';
import { SearchBar } from '../components/SearchBar.tsx';
import { SortSelect } from '../components/SortSelect.tsx';
import { useCafeSearch } from '../hooks/useCafeSearch.ts';

/**
 * Cafe discovery: search, filters, location, sorting, ranked results,
 * and a synchronized map. All data comes from GET /api/search; map and
 * cards render the same result state keyed by osm_id.
 */
export function DiscoverPage() {
  const { filters, updateFilters, clearFilters, state, retry } = useCafeSearch();
  const [selectedOsmId, setSelectedOsmId] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<'list' | 'map'>('list');
  const cardRefs = useRef(new Map<string, HTMLElement>());

  useEffect(() => {
    setSelectedOsmId(null);
  }, [state.results]);

  useEffect(() => {
    if (selectedOsmId === null) return;
    cardRefs.current.get(selectedOsmId)?.scrollIntoView({ block: 'nearest' });
  }, [selectedOsmId]);

  const lat = filters.lat.trim() === '' ? null : Number(filters.lat);
  const lon = filters.lon.trim() === '' ? null : Number(filters.lon);
  const radius = filters.radius.trim() === '' ? null : Number(filters.radius);
  const mapCenter: [number, number] | null =
    lat !== null && lon !== null && Number.isFinite(lat) && Number.isFinite(lon)
      ? [lat, lon]
      : null;
  const mapRadius = radius !== null && Number.isFinite(radius) && radius >= 0 ? radius : null;
  const mapNotice =
    state.status === 'empty'
      ? 'No matching cafes to map.'
      : state.results.length > 0 &&
          !state.results.some((cafe) => typeof cafe.latitude === 'number' && typeof cafe.longitude === 'number')
        ? 'No mapped cafe locations are available for these results.'
        : null;

  const registerCard = (osmId: string) => (element: HTMLElement | null) => {
    if (element === null) {
      cardRefs.current.delete(osmId);
    } else {
      cardRefs.current.set(osmId, element);
    }
  };

  return (
    <div className="discover">
      <section className="panel" aria-label="Cafe discovery">
        <h2>Find cafes</h2>
        <SearchBar value={filters.name} onChange={(value) => updateFilters({ name: value })} />
        <FilterPanel
          cuisine={filters.cuisine}
          hasWebsite={filters.hasWebsite}
          hasPhone={filters.hasPhone}
          hasHours={filters.hasHours}
          lat={filters.lat}
          lon={filters.lon}
          radius={filters.radius}
          onCuisineChange={(cuisine) => updateFilters({ cuisine })}
          onHasWebsiteChange={(hasWebsite) => updateFilters({ hasWebsite })}
          onHasPhoneChange={(hasPhone) => updateFilters({ hasPhone })}
          onHasHoursChange={(hasHours) => updateFilters({ hasHours })}
          onLatChange={(lat) => updateFilters({ lat })}
          onLonChange={(lon) => updateFilters({ lon })}
          onRadiusChange={(radius) => updateFilters({ radius })}
          onClear={clearFilters}
        />
        <SortSelect value={filters.sortBy} onChange={(sortBy) => updateFilters({ sortBy })} />
      </section>

      <div className="content">
        <div className="view-toggle" role="group" aria-label="Results view">
          <button
            type="button"
            aria-pressed={mobileView === 'list'}
            className={mobileView === 'list' ? 'view-toggle-active' : undefined}
            onClick={() => setMobileView('list')}
          >
            List
          </button>
          <button
            type="button"
            aria-pressed={mobileView === 'map'}
            className={mobileView === 'map' ? 'view-toggle-active' : undefined}
            onClick={() => setMobileView('map')}
          >
            Map
          </button>
        </div>

        <section
          className={`results ${mobileView === 'map' ? 'results-hidden-mobile' : ''}`}
          aria-label="Results"
          aria-busy={state.status === 'loading'}
        >
        <div aria-live="polite">
          {state.status === 'loading' && <LoadingState />}
          {state.status === 'error' && state.error !== null && (
            <ErrorState message={state.error} onRetry={retry} />
          )}
          {state.status === 'empty' && <EmptyState onClear={clearFilters} />}
          {state.status === 'success' && (
            <p className="count">
              {state.count} {state.count === 1 ? 'cafe' : 'cafes'} found
            </p>
          )}
        </div>
        {state.status === 'success' && (
          <div className="cards">
            {state.results.map((cafe) => (
              <div
                key={cafe.osm_id}
                ref={registerCard(cafe.osm_id)}
                className={cafe.osm_id === selectedOsmId ? 'card-selected' : undefined}
                onClick={() => setSelectedOsmId(cafe.osm_id)}
              >
                <CafeCard cafe={cafe} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section
        className={`map-pane ${mobileView === 'map' ? 'map-pane-visible-mobile' : ''}`}
        aria-label="Cafe map"
      >
        <CafeMap
          cafes={state.results}
          selectedOsmId={selectedOsmId}
          onSelect={setSelectedOsmId}
          center={mapCenter}
          radiusKm={mapRadius}
          notice={mapNotice}
        />
      </section>
      </div>
    </div>
  );
}

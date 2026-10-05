import { useEffect } from 'react';
import L from 'leaflet';
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { CafeResult } from '../api/types.ts';
import { detailHash } from '../routing.ts';

/**
 * Fallback map center, used only when no result has usable coordinates.
 * Taken from the project's documented demo location (README), not from
 * the dataset — the map otherwise fits itself to real result coordinates.
 */
const FALLBACK_CENTER: [number, number] = [26.8467, 80.9462];
const FALLBACK_ZOOM = 11;

interface MappedCafe {
  osmId: string;
  name: string;
  lat: number;
  lon: number;
  cuisine: string | null;
  distanceKm: number | null;
  scoreTotal: number | null;
}

/** Finite-number guard: Leaflet cannot render missing coordinates,
 *  so only finite values become markers. Range validity stays
 *  server-side; this guards renderability, not data quality. */
function toMapped(cafe: CafeResult): MappedCafe | null {
  if (
    typeof cafe.latitude !== 'number' ||
    typeof cafe.longitude !== 'number' ||
    !Number.isFinite(cafe.latitude) ||
    !Number.isFinite(cafe.longitude)
  ) {
    return null;
  }
  return {
    osmId: cafe.osm_id,
    name: cafe.name ?? 'Name unavailable in dataset',
    lat: cafe.latitude,
    lon: cafe.longitude,
    cuisine: cafe.cuisine,
    distanceKm: cafe.distance_km,
    scoreTotal: cafe.score_total,
  };
}

function markerIcon(selected: boolean) {
  return L.divIcon({
    html: `<span class="cf-marker${selected ? ' cf-marker-selected' : ''}"></span>`,
    className: 'cf-marker-wrap',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function ViewController({
  points,
  fitKey,
  selected,
}: {
  points: Array<[number, number]>;
  fitKey: string;
  selected: MappedCafe | null;
}) {
  const map = useMap();
  const selectedKey = selected === null ? '' : `${selected.lat},${selected.lon}`;
  useEffect(() => {
    if (points.length === 0) return;
    map.fitBounds(L.latLngBounds(points.map(([lat, lon]) => L.latLng(lat, lon))), {
      padding: [32, 32],
    });
  }, [map, fitKey]);
  useEffect(() => {
    if (selected !== null) {
      map.panTo([selected.lat, selected.lon], { animate: false });
    }
  }, [map, selectedKey]);
  return null;
}

export interface CafeMapProps {
  cafes: CafeResult[];
  selectedOsmId: string | null;
  onSelect: (osmId: string) => void;
  center: [number, number] | null;
  radiusKm: number | null;
  notice: string | null;
}

/**
 * Presentation-only map. Receives cafes from Discover state, never
 * fetches. Marker identity is always `osm_id`. The radius circle is a
 * visual of the API's own radius value — membership stays server-side.
 */
export function CafeMap({ cafes, selectedOsmId, onSelect, center, radiusKm, notice }: CafeMapProps) {
  const mapped: MappedCafe[] = [];
  for (const cafe of cafes) {
    const point = toMapped(cafe);
    if (point !== null) mapped.push(point);
  }
  const positions = mapped.map((m) => [m.lat, m.lon] as [number, number]);
  const fitKey = JSON.stringify(positions);
  const selected = mapped.find((m) => m.osmId === selectedOsmId) ?? null;
  const showRadius =
    center !== null && radiusKm !== null && Number.isFinite(radiusKm) && radiusKm >= 0;

  return (
    <div className="map-wrap">
      <MapContainer
        center={FALLBACK_CENTER}
        zoom={FALLBACK_ZOOM}
        scrollWheelZoom
        className="map"
        aria-label="Map of cafe locations"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ViewController points={positions} fitKey={fitKey} selected={selected} />
        {mapped.map((point) => (
          <Marker
            key={point.osmId}
            position={[point.lat, point.lon]}
            icon={markerIcon(point.osmId === selectedOsmId)}
            title={point.name}
            keyboard
            eventHandlers={{ click: () => onSelect(point.osmId) }}
          >
            <Popup>
              <strong>{point.name}</strong>
              {point.cuisine !== null && point.cuisine !== '' && <span> · {point.cuisine}</span>}
              {point.distanceKm !== null && <span> · {point.distanceKm.toFixed(2)} km</span>}
              {point.scoreTotal !== null && <span> · Score {point.scoreTotal}/100</span>}
              <br />
              <a href={detailHash(point.osmId)}>View details</a>
            </Popup>
          </Marker>
        ))}
        {showRadius && center !== null && radiusKm !== null && (
          <Circle
            center={center}
            radius={radiusKm * 1000}
            pathOptions={{ color: '#0b6e99', weight: 2, dashArray: '6 6', fillOpacity: 0.06 }}
            className="cf-radius"
          />
        )}
      </MapContainer>
      {notice !== null && <p className="map-notice">{notice}</p>}
    </div>
  );
}

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { CafeResult } from '../api/types.ts';
import { CafeMap } from './CafeMap.tsx';

afterEach(() => {
  cleanup();
});

function cafe(overrides: Partial<CafeResult> & { osm_id: string }): CafeResult {
  const { osm_id, ...rest } = overrides;
  return {
    osm_id,
    name: null,
    latitude: null,
    longitude: null,
    street: null,
    housenumber: null,
    city: null,
    postcode: null,
    cuisine: null,
    opening_hours: null,
    website: null,
    phone: null,
    source: null,
    distance_km: null,
    score_distance: null,
    score_cuisine: null,
    score_opening_hours: null,
    score_website: null,
    score_phone: null,
    score_total: null,
    score_reasons: null,
    ...rest,
  };
}

const PLOT_A = cafe({ osm_id: 'node-a', name: 'Alpha', latitude: 26.85, longitude: 80.94 });
const PLOT_B = cafe({ osm_id: 'node-b', name: 'Beta', latitude: 26.86, longitude: 80.95 });
const NO_COORDS = cafe({ osm_id: 'node-c', name: 'Gamma' });

describe('CafeMap', () => {
  it('renders one marker per cafe with valid coordinates', () => {
    const { container } = render(
      <CafeMap cafes={[PLOT_A, PLOT_B, NO_COORDS]} selectedOsmId={null} onSelect={() => undefined} center={null} radiusKm={null} notice={null} />,
    );
    expect(container.querySelectorAll('.cf-marker')).toHaveLength(2);
  });

  it('creates no markers for missing coordinates', () => {
    const { container } = render(
      <CafeMap cafes={[NO_COORDS]} selectedOsmId={null} onSelect={() => undefined} center={null} radiusKm={null} notice={null} />,
    );
    expect(container.querySelectorAll('.cf-marker')).toHaveLength(0);
  });

  it('identifies markers by cafe name for assistive technology', () => {
    render(
      <CafeMap cafes={[PLOT_A]} selectedOsmId={null} onSelect={() => undefined} center={null} radiusKm={null} notice={null} />,
    );
    expect(screen.getByTitle('Alpha')).toBeInTheDocument();
  });

  it('notifies the parent with the osm_id when a marker is clicked', () => {
    const onSelect = vi.fn();
    render(
      <CafeMap cafes={[PLOT_A, PLOT_B]} selectedOsmId={null} onSelect={onSelect} center={null} radiusKm={null} notice={null} />,
    );
    fireEvent.click(screen.getByTitle('Beta'));
    expect(onSelect).toHaveBeenCalledWith('node-b');
  });

  it('marks the selected cafe distinctly', () => {
    const { container } = render(
      <CafeMap cafes={[PLOT_A, PLOT_B]} selectedOsmId="node-b" onSelect={() => undefined} center={null} radiusKm={null} notice={null} />,
    );
    const selected = container.querySelectorAll('.cf-marker-selected');
    expect(selected).toHaveLength(1);
  });

  it('shows the radius circle only when center and radius are active', () => {
    const withRadius = render(
      <CafeMap cafes={[PLOT_A]} selectedOsmId={null} onSelect={() => undefined} center={[26.85, 80.94]} radiusKm={3} notice={null} />,
    );
    expect(withRadius.container.querySelectorAll('.cf-radius')).toHaveLength(1);
    withRadius.unmount();
    const withoutRadius = render(
      <CafeMap cafes={[PLOT_A]} selectedOsmId={null} onSelect={() => undefined} center={null} radiusKm={null} notice={null} />,
    );
    expect(withoutRadius.container.querySelectorAll('.cf-radius')).toHaveLength(0);
  });

  it('shows the empty notice instead of markers when there is nothing mapped', () => {
    render(
      <CafeMap cafes={[]} selectedOsmId={null} onSelect={() => undefined} center={null} radiusKm={null} notice="No cafes match the current filters." />,
    );
    expect(screen.getByText('No cafes match the current filters.')).toBeInTheDocument();
  });

  it('keeps OpenStreetMap attribution visible', () => {
    render(
      <CafeMap cafes={[PLOT_A]} selectedOsmId={null} onSelect={() => undefined} center={null} radiusKm={null} notice={null} />,
    );
    expect(screen.getByText(/OpenStreetMap/)).toBeInTheDocument();
  });
});

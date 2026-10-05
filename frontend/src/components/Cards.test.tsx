import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { CafeResult } from '../api/types.ts';
import { CafeCard } from './CafeCard.tsx';
import { ScoreBreakdown } from './ScoreBreakdown.tsx';
import { EmptyState, ErrorState, LoadingState } from './StatusStates.tsx';

afterEach(() => {
  cleanup();
});

function completeCafe(): CafeResult {
  return {
    osm_id: 'node1',
    name: 'Cafe Coffee Day',
    latitude: 26.85,
    longitude: 80.94,
    street: 'Ashok Marg',
    housenumber: null,
    city: 'Lucknow',
    postcode: '226001',
    cuisine: 'coffee_shop',
    opening_hours: '09:00-22:00',
    website: 'https://example.org',
    phone: null,
    source: null,
    distance_km: 0.8,
    score_distance: 40,
    score_cuisine: 30,
    score_opening_hours: 15,
    score_website: 10,
    score_phone: 0,
    score_total: 95,
    score_reasons: ['Distance: 0.8 km → 40 points', 'Phone unavailable in dataset → 0 points'],
  };
}

function sparseCafe(): CafeResult {
  return {
    osm_id: 'node2',
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
  };
}

describe('CafeCard', () => {
  it('renders real API data including score and distance', () => {
    render(<CafeCard cafe={completeCafe()} />);
    expect(screen.getByRole('heading', { name: 'Cafe Coffee Day' })).toBeInTheDocument();
    expect(screen.getByText(/0\.80 km/)).toBeInTheDocument();
    expect(screen.getByText(/Score: 95\/100/)).toBeInTheDocument();
    expect(screen.getByText('https://example.org')).toBeInTheDocument();
  });

  it('labels every missing field as unavailable in the dataset', () => {
    render(<CafeCard cafe={sparseCafe()} />);
    expect(screen.getByText(/Name unavailable in dataset/)).toBeInTheDocument();
    expect(screen.getByText(/Cuisine unavailable in dataset/)).toBeInTheDocument();
    expect(screen.getByText(/Address unavailable in dataset/)).toBeInTheDocument();
    expect(screen.getByText(/Website unavailable in dataset/)).toBeInTheDocument();
    expect(screen.getByText(/Phone unavailable in dataset/)).toBeInTheDocument();
    expect(screen.getByText(/Opening hours unavailable in dataset/)).toBeInTheDocument();
    expect(screen.queryByText(/Score:/)).not.toBeInTheDocument();
  });
});

describe('ScoreBreakdown', () => {
  it('renders the total and the verbatim API reasons', () => {
    render(<ScoreBreakdown cafe={completeCafe()} />);
    expect(screen.getByText(/Score: 95\/100/)).toBeInTheDocument();
    expect(screen.getByText(/Distance: 0\.8 km → 40 points/)).toBeInTheDocument();
    expect(screen.getByText(/Phone unavailable in dataset → 0 points/)).toBeInTheDocument();
  });

  it('renders component points without inventing maxima', () => {
    const { container } = render(<ScoreBreakdown cafe={completeCafe()} />);
    expect(container.textContent).not.toMatch(/\/(40|30|15|10|5)(?!\d)/);
  });

  it('renders nothing when the API returned no scores', () => {
    const { container } = render(<ScoreBreakdown cafe={sparseCafe()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('Status states', () => {
  it('loading state announces itself to assistive technology', () => {
    render(<LoadingState />);
    expect(screen.getByRole('status')).toHaveTextContent(/loading cafes/i);
  });

  it('empty state explains and offers to clear filters', () => {
    const onClear = vi.fn();
    render(<EmptyState onClear={onClear} />);
    expect(screen.getByText(/no cafes match/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /clear filters/i }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it('error state is an alert with a retry action', () => {
    const onRetry = vi.fn();
    render(<ErrorState message="API is down." onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toHaveTextContent(/API is down\./);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

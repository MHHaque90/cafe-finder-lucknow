import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { CafeResult } from '../api/types.ts';
import { DiscoverPage } from './DiscoverPage.tsx';

const FULL_CAFE: CafeResult = {
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
  website: null,
  phone: null,
  source: null,
  distance_km: null,
  score_distance: 0,
  score_cuisine: 30,
  score_opening_hours: 15,
  score_website: 0,
  score_phone: 0,
  score_total: 45,
  score_reasons: ['Cuisine match: coffee_shop → 30 points'],
};

const SPARSE_CAFE: CafeResult = {
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

let requestedUrls: string[];
let nextResponse: { ok: boolean; status: number; body: unknown };

function mockApi() {
  requestedUrls = [];
  nextResponse = { ok: true, status: 200, body: { count: 2, results: [FULL_CAFE, SPARSE_CAFE] } };
  vi.stubGlobal(
    'fetch',
    vi.fn((url: unknown) => {
      requestedUrls.push(String(url));
      const current = nextResponse;
      return Promise.resolve({
        ok: current.ok,
        status: current.status,
        json: () => Promise.resolve(current.body),
      });
    }),
  );
}

function lastUrl(): string {
  return requestedUrls[requestedUrls.length - 1] ?? '';
}

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  mockApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('DiscoverPage', () => {
  it('shows a loading state on initial render', () => {
    render(<DiscoverPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders cards and a truthful count on success', async () => {
    render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Cafe Coffee Day' })).toBeInTheDocument();
    expect(screen.getByText(/Score: 45\/100/)).toBeInTheDocument();
    // Both fixture cafes lack websites, and both say so honestly.
    expect(screen.getAllByText(/Website unavailable in dataset/)).toHaveLength(2);
  });

  it('shows the empty state when the API returns zero results', async () => {
    nextResponse = { ok: true, status: 200, body: { count: 0, results: [] } };
    render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText(/no cafes match/i)).toBeInTheDocument());
    expect(screen.queryByRole('heading', { name: 'Cafe Coffee Day' })).not.toBeInTheDocument();
  });

  it('shows an error state with retry on API failure', async () => {
    nextResponse = { ok: false, status: 500, body: { detail: 'boom' } };
    render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText(/boom/)).toBeInTheDocument();
    const callsBefore = requestedUrls.length;
    nextResponse = { ok: true, status: 200, body: { count: 0, results: [] } };
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(callsBefore));
  });

  it('sends typed search text as the name parameter', async () => {
    render(<DiscoverPage />);
    fireEvent.change(screen.getByLabelText(/search/i), { target: { value: 'chai' } });
    await waitFor(() => expect(lastUrl()).toContain('name=chai'));
  });

  it('sends the selected cuisine tag', async () => {
    render(<DiscoverPage />);
    fireEvent.change(screen.getByLabelText(/cuisine/i), { target: { value: 'tea_shop' } });
    await waitFor(() => expect(lastUrl()).toContain('cuisine=tea_shop'));
  });

  it('sends boolean filters only when enabled', async () => {
    render(<DiscoverPage />);
    fireEvent.click(screen.getByLabelText(/website/i));
    await waitFor(() => expect(lastUrl()).toContain('has_website=true'));
  });

  it('sends the selected sort mode', async () => {
    render(<DiscoverPage />);
    fireEvent.change(screen.getByLabelText(/^sort$/i), { target: { value: 'name' } });
    await waitFor(() => expect(lastUrl()).toContain('sort_by=name'));
  });

  it('initializes filter state from the URL', async () => {
    window.history.replaceState(null, '', '/?cuisine=tea&sort_by=score');
    render(<DiscoverPage />);
    await waitFor(() => expect(lastUrl()).toContain('cuisine=tea'));
    expect(screen.getByLabelText(/cuisine/i)).toHaveValue('tea');
  });

  it('clear filters resets inputs and refetches unfiltered', async () => {
    window.history.replaceState(null, '', '/?cuisine=tea&sort_by=name');
    render(<DiscoverPage />);
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));
    const callsBefore = requestedUrls.length;
    fireEvent.click(screen.getByRole('button', { name: /clear filters/i }));
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(callsBefore));
    expect(lastUrl()).toContain('sort_by=score');
    expect(lastUrl()).not.toContain('cuisine=');
    expect(screen.getByLabelText(/search/i)).toHaveValue('');
  });

  it('validates radius locally without calling the API', async () => {
    render(<DiscoverPage />);
    await waitFor(() => expect(requestedUrls.length).toBeGreaterThan(0));
    const callsBefore = requestedUrls.length;
    fireEvent.change(screen.getByLabelText(/radius/i), { target: { value: '3' } });
    await waitFor(() => expect(screen.getByText(/requires latitude and longitude/i)).toBeInTheDocument());
    expect(requestedUrls.length).toBe(callsBefore);
  });

  it('renders one map marker per result with coordinates', async () => {
    const { container } = render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    expect(container.querySelectorAll('.cf-marker')).toHaveLength(1);
  });

  it('selects the card when its marker is clicked', async () => {
    const { container } = render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    const marker = container.querySelector('.cf-marker');
    expect(marker).not.toBeNull();
    if (marker !== null) fireEvent.click(marker);
    await waitFor(() =>
      expect(container.querySelector('.card-selected')).not.toBeNull(),
    );
  });

  it('links each card to its detail route by osm_id', async () => {
    render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    const links = screen.getAllByRole('link', { name: /view details/i });
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute('href', '#/cafes/node1');
    expect(links[1]).toHaveAttribute('href', '#/cafes/node2');
  });

  it('shows the radius circle when a location radius search is active', async () => {
    window.history.replaceState(null, '', '/?lat=26.8467&lon=80.9462&radius=3');
    const { container } = render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText(/cafes found/)).toBeInTheDocument());
    expect(container.querySelectorAll('.cf-radius')).toHaveLength(1);
  });

  it('toggles card selection from the keyboard-operable highlight button', async () => {
    const { container } = render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    const highlights = screen.getAllByRole('button', { name: 'Highlight on map' });
    expect(highlights).toHaveLength(2);
    expect(highlights[0]).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(highlights[0]);
    await waitFor(() =>
      expect(container.querySelector('.card-selected')).not.toBeNull(),
    );
    expect(screen.getByRole('button', { name: 'Unhighlight on map' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('labels the results and map regions with headings', async () => {
    render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Results' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Cafe map' })).toBeInTheDocument();
  });

  it('exposes the mobile list/map switch as pressed-group buttons', async () => {
    render(<DiscoverPage />);
    await waitFor(() => expect(screen.getByText('2 cafes found')).toBeInTheDocument());
    const listButton = screen.getByRole('button', { name: 'List' });
    const mapButton = screen.getByRole('button', { name: 'Map' });
    expect(listButton).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(mapButton);
    expect(mapButton).toHaveAttribute('aria-pressed', 'true');
    expect(listButton).toHaveAttribute('aria-pressed', 'false');
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import { getCafes, getCafe, getHealth, getQuality, searchCafes } from './client.ts';
import { ApiRequestError } from './types.ts';

function mockFetchOnce(body: unknown, init: { ok: boolean; status: number }) {
  const response = {
    ok: init.ok,
    status: init.status,
    statusText: init.ok ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
  };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
  return vi.mocked(fetch);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('searchCafes request building', () => {
  it('sends filters as query parameters', async () => {
    const stub = mockFetchOnce({ count: 0, results: [] }, { ok: true, status: 200 });
    await searchCafes({ cuisine: 'coffee_shop', has_website: true, sort_by: 'score' });
    const url = String(stub.mock.calls[0]?.[0] ?? '');
    expect(url).toContain('/api/search');
    expect(url).toContain('cuisine=coffee_shop');
    expect(url).toContain('has_website=true');
    expect(url).toContain('sort_by=score');
  });

  it('omits unset and false filters', async () => {
    const stub = mockFetchOnce({ count: 0, results: [] }, { ok: true, status: 200 });
    await searchCafes({ has_phone: false });
    const url = String(stub.mock.calls[0]?.[0] ?? '');
    expect(url).toBe('http://127.0.0.1:8000/api/search');
  });

  it('sends location and radius parameters', async () => {
    const stub = mockFetchOnce({ count: 0, results: [] }, { ok: true, status: 200 });
    await searchCafes({ lat: 26.8, lon: 80.9, radius: 3 });
    const url = String(stub.mock.calls[0]?.[0] ?? '');
    expect(url).toContain('lat=26.8');
    expect(url).toContain('lon=80.9');
    expect(url).toContain('radius=3');
  });
});

describe('API error handling', () => {
  it('throws the server detail message on HTTP errors', async () => {
    mockFetchOnce({ detail: 'Error: --radius must be non-negative' }, { ok: false, status: 400 });
    const error = await searchCafes({ radius: -1 }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect((error as ApiRequestError).status).toBe(400);
    expect((error as Error).message).toContain('--radius must be non-negative');
  });

  it('falls back to a status message when the body has no detail', async () => {
    mockFetchOnce({}, { ok: false, status: 500 });
    const error = await getCafes({}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect((error as Error).message).toContain('500');
  });

  it('reports unreachable API without raw exceptions', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fetch failed')));
    const error = await getHealth().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect((error as Error).message).toContain('Unable to reach');
    expect((error as Error).message).not.toContain('TypeError');
  });
});

describe('getHealth and getCafes', () => {
  it('requests the health endpoint', async () => {
    const stub = mockFetchOnce({ status: 'ok' }, { ok: true, status: 200 });
    await getHealth();
    expect(String(stub.mock.calls[0]?.[0] ?? '')).toContain('/api/health');
  });

  it('requests the cafes endpoint', async () => {
    const stub = mockFetchOnce({ count: 1, results: [] }, { ok: true, status: 200 });
    const body = await getCafes({ name: 'cafe' });
    expect(String(stub.mock.calls[0]?.[0] ?? '')).toContain('/api/cafes?');
    expect(body.count).toBe(1);
  });

  it('requests a single cafe by encoded id with optional cuisine', async () => {
    const stub = mockFetchOnce({ osm_id: 'node 1' }, { ok: true, status: 200 });
    await getCafe('node 1', 'tea');
    const url = String(stub.mock.calls[0]?.[0] ?? '');
    expect(url).toContain('/api/cafes/node%201');
    expect(url).toContain('cuisine=tea');
  });

  it('omits the cuisine parameter when absent', async () => {
    const stub = mockFetchOnce({ osm_id: 'node1' }, { ok: true, status: 200 });
    await getCafe('node1');
    expect(String(stub.mock.calls[0]?.[0] ?? '')).toBe('http://127.0.0.1:8000/api/cafes/node1');
  });

  it('requests the quality endpoint', async () => {
    const stub = mockFetchOnce({ report: {}, provenance: {}, records: [] }, { ok: true, status: 200 });
    await getQuality();
    expect(String(stub.mock.calls[0]?.[0] ?? '')).toContain('/api/quality');
  });
});

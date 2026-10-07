import { describe, expect, it } from 'vitest';
import { compareHash, detailHash, parseHashRoute } from './routing.ts';

describe('parseHashRoute', () => {
  it('maps empty and root hashes to Discover', () => {
    expect(parseHashRoute('')).toEqual({ name: 'discover' });
    expect(parseHashRoute('#/')).toEqual({ name: 'discover' });
  });

  it('parses detail routes with a stable osm_id', () => {
    expect(parseHashRoute('#/cafes/node123')).toEqual({ name: 'detail', osmId: 'node123' });
  });

  it('decodes percent-encoded osm ids', () => {
    expect(parseHashRoute('#/cafes/node%20123')).toEqual({ name: 'detail', osmId: 'node 123' });
  });

  it('falls back to Discover for malformed or empty ids', () => {
    expect(parseHashRoute('#/cafes/')).toEqual({ name: 'discover' });
    expect(parseHashRoute('#/unknown')).toEqual({ name: 'discover' });
    expect(parseHashRoute('#/cafes/%E0%A4%A')).toEqual({ name: 'discover' });
  });

  it('parses the analytics and quality routes', () => {
    expect(parseHashRoute('#/analytics')).toEqual({ name: 'analytics' });
    expect(parseHashRoute('#/quality')).toEqual({ name: 'quality' });
  });

  it('parses the history, integrity, and lineage routes', () => {
    expect(parseHashRoute('#/history')).toEqual({ name: 'history' });
    expect(parseHashRoute('#/integrity')).toEqual({ name: 'integrity' });
    expect(parseHashRoute('#/lineage')).toEqual({ name: 'lineage' });
  });

  it('parses compare routes with baseline and target', () => {
    expect(parseHashRoute('#/history/compare?baseline=a&target=b')).toEqual({
      name: 'compare',
      baseline: 'a',
      target: 'b',
    });
    expect(parseHashRoute('#/history/compare')).toEqual({
      name: 'compare',
      baseline: null,
      target: null,
    });
    expect(parseHashRoute('#/history/compare?baseline=a')).toEqual({
      name: 'compare',
      baseline: 'a',
      target: null,
    });
  });
});

describe('detailHash', () => {
  it('encodes the osm_id safely', () => {
    expect(detailHash('node 1/2')).toBe('#/cafes/node%201%2F2');
  });
});

describe('compareHash', () => {
  it('builds a compare hash with encoded parameters', () => {
    expect(compareHash('2026-01-01T000000Z', '2026-02-01T000000Z')).toBe(
      '#/history/compare?baseline=2026-01-01T000000Z&target=2026-02-01T000000Z',
    );
  });
});

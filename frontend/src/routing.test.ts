import { describe, expect, it } from 'vitest';
import { detailHash, parseHashRoute } from './routing.ts';

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
});

describe('detailHash', () => {
  it('encodes the osm_id safely', () => {
    expect(detailHash('node 1/2')).toBe('#/cafes/node%201%2F2');
  });
});

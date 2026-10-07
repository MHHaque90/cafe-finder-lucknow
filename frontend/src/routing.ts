/**
 * Minimal hash router.
 *
 * Routes: `#/` (Discover), `#/cafes/:osmId` (detail), `#/analytics`,
 * `#/quality`, `#/history`, `#/history/compare`, `#/integrity`, and
 * `#/lineage`. Hash routing keeps every route servable from a static
 * file server (no history-fallback rewrites needed) and preserves the
 * real query string, so Discover filter state survives detail navigation
 * and back/forward.
 */
import { useEffect, useState } from 'react';

export type Route =
  | { name: 'discover' }
  | { name: 'detail'; osmId: string }
  | { name: 'analytics' }
  | { name: 'quality' }
  | { name: 'history' }
  | { name: 'compare'; baseline: string | null; target: string | null }
  | { name: 'integrity' }
  | { name: 'lineage' };

export function detailHash(osmId: string): string {
  return `#/cafes/${encodeURIComponent(osmId)}`;
}

export function compareHash(baseline: string, target: string): string {
  const query = new URLSearchParams({ baseline, target }).toString();
  return `#/history/compare?${query}`;
}

export function parseHashRoute(hash: string): Route {
  if (hash === '#/analytics') return { name: 'analytics' };
  if (hash === '#/quality') return { name: 'quality' };
  if (hash === '#/history') return { name: 'history' };
  if (hash === '#/integrity') return { name: 'integrity' };
  if (hash === '#/lineage') return { name: 'lineage' };
  if (hash === '#/history/compare' || hash.startsWith('#/history/compare?')) {
    const queryIndex = hash.indexOf('?');
    const params =
      queryIndex >= 0 ? new URLSearchParams(hash.slice(queryIndex + 1)) : null;
    const baseline = params?.get('baseline') ?? null;
    const target = params?.get('target') ?? null;
    return {
      name: 'compare',
      baseline: baseline === '' ? null : baseline,
      target: target === '' ? null : target,
    };
  }
  const match = /^#\/cafes\/([^/?#]+)/.exec(hash);
  if (match) {
    try {
      const osmId = decodeURIComponent(match[1]);
      if (osmId !== '') return { name: 'detail', osmId };
    } catch {
      // Malformed percent-encoding falls through to Discover.
    }
  }
  return { name: 'discover' };
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHashRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => {
      setRoute(parseHashRoute(window.location.hash));
    };
    window.addEventListener('hashchange', onChange);
    return () => {
      window.removeEventListener('hashchange', onChange);
    };
  }, []);
  return route;
}

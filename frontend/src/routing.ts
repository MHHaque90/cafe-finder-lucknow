/**
 * Minimal hash router.
 *
 * Two routes only: `#/` (Discover) and `#/cafes/:osmId` (detail). Hash
 * routing keeps every route servable from a static file server (no
 * history-fallback rewrites needed) and preserves the real query string,
 * so Discover filter state survives detail navigation and back/forward.
 */
import { useEffect, useState } from 'react';

export type Route =
  | { name: 'discover' }
  | { name: 'detail'; osmId: string }
  | { name: 'analytics' }
  | { name: 'quality' };

export function detailHash(osmId: string): string {
  return `#/cafes/${encodeURIComponent(osmId)}`;
}

export function parseHashRoute(hash: string): Route {
  if (hash === '#/analytics') return { name: 'analytics' };
  if (hash === '#/quality') return { name: 'quality' };
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

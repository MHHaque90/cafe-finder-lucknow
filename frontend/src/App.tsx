import { AnalyticsPage } from './pages/AnalyticsPage.tsx';
import { CafeDetailPage } from './pages/CafeDetailPage.tsx';
import { ComparePage } from './pages/ComparePage.tsx';
import { DiscoverPage } from './pages/DiscoverPage.tsx';
import { HistoryPage } from './pages/HistoryPage.tsx';
import { IntegrityPage } from './pages/IntegrityPage.tsx';
import { LineagePage } from './pages/LineagePage.tsx';
import { QualityPage } from './pages/QualityPage.tsx';
import { useHashRoute } from './routing.ts';

export default function App() {
  const route = useHashRoute();
  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>
            <a href="#/">Cafe Finder</a>
          </h1>
          <p className="tagline">Lucknow cafe discovery from OpenStreetMap data</p>
        </div>
        <nav aria-label="Primary">
          <a href="#/" aria-current={route.name === 'discover' ? 'page' : undefined}>
            Discover
          </a>{' '}
          <a href="#/analytics" aria-current={route.name === 'analytics' ? 'page' : undefined}>
            Analytics
          </a>{' '}
          <a href="#/quality" aria-current={route.name === 'quality' ? 'page' : undefined}>
            Data Quality
          </a>{' '}
          <a href="#/history" aria-current={route.name === 'history' ? 'page' : undefined}>
            History
          </a>{' '}
          <a href="#/integrity" aria-current={route.name === 'integrity' ? 'page' : undefined}>
            Integrity
          </a>{' '}
          <a href="#/lineage" aria-current={route.name === 'lineage' ? 'page' : undefined}>
            Lineage
          </a>
        </nav>
      </header>
      <main>
        {route.name === 'detail' ? (
          <CafeDetailPage key={route.osmId} osmId={route.osmId} />
        ) : route.name === 'analytics' ? (
          <AnalyticsPage />
        ) : route.name === 'quality' ? (
          <QualityPage />
        ) : route.name === 'history' ? (
          <HistoryPage />
        ) : route.name === 'compare' ? (
          <ComparePage baseline={route.baseline} target={route.target} />
        ) : route.name === 'integrity' ? (
          <IntegrityPage />
        ) : route.name === 'lineage' ? (
          <LineagePage />
        ) : (
          <DiscoverPage />
        )}
      </main>
      <footer className="app-footer">
        <p>
          Data: OpenStreetMap contributors (ODbL 1.0) via Overpass API.{' '}
          <a href="https://www.openstreetmap.org/copyright">Attribution</a>. Missing
          fields are reported, never fabricated.
        </p>
      </footer>
    </div>
  );
}

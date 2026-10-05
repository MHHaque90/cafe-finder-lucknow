export function LoadingState() {
  return (
    <div className="status" role="status" aria-label="Loading cafes">
      <div className="skeleton" aria-hidden="true">
        <div className="skeleton-line" />
        <div className="skeleton-line skeleton-line-short" />
      </div>
      <p>Loading cafes…</p>
    </div>
  );
}

interface EmptyStateProps {
  onClear: () => void;
}

export function EmptyState({ onClear }: EmptyStateProps) {
  return (
    <div className="status">
      <p>No cafes match the current filters.</p>
      <p>Try removing a filter or widening the search radius.</p>
      <button type="button" className="button-secondary" onClick={onClear}>
        Clear filters
      </button>
    </div>
  );
}

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="status status-error" role="alert">
      <p>Unable to load cafes.</p>
      <p>{message}</p>
      <p>Check that the Cafe Finder API is running, then try again.</p>
      <button type="button" className="button-secondary" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}

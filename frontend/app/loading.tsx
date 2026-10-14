export default function Loading() {
  return <div className="route-loading" role="status" aria-label="Loading page">
    <span className="sr-only">Loading page…</span>
    <div className="route-skeleton-title" aria-hidden="true" />
    <div className="route-skeleton-description" aria-hidden="true" />
    <div className="route-skeleton-panel" aria-hidden="true"><span /><span /><span /></div>
  </div>;
}

"use client";

export type ReviewView = "overview" | "evidence" | "report" | "history";

export function ReviewTabs({ value, onChange, disabled = false }: { value: ReviewView; onChange: (view: ReviewView) => void; disabled?: boolean }) {
  return <nav aria-label="Report sections" className="review-tabs">
    {([['overview', 'Inspect'], ['report', 'Report'], ['history', 'History']] as const).map(([view, label]) =>
      <button key={view} type="button" disabled={disabled} aria-pressed={value === view} onClick={() => onChange(view)} className="review-tab">{label}</button>
    )}
  </nav>;
}

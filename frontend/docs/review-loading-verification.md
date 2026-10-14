# Independent incident review loading

2026-10-12. Frontend-only scope: V1 review workspace. No API contract, backend,
V2 workspace, editor/workflow permission, or shared service changes.

Metadata, report and evidence now publish separately when their own request
finishes. Each has loading/error/retry; an error leaves successful sections
visible. Retrying only repeats the failed resource. Evidence seek stays disabled
until metadata supplies a valid V1 collision-relative-to-video offset.

Audit loads independently once on initial production page load. Report hydration
does not trigger another audit request. Successful save/workflow updates with a
new report version refresh audit explicitly; audit also has its own Retry.

The workspace subtree is keyed by incident ID, resetting editors, media and all
resource states on navigation. Each resource effect ignores its responses after
cleanup, including errors and loading completion. Requests may still finish in
the transport; they cannot update the new incident's state.

Checks run against the current working tree, which includes existing staged auth
integration, using an isolated production frontend copy to avoid shared Next cache
interference:

- `npm run typecheck`, `npm run lint`, `npm run build`: passed.
- `node tests/review-draft-regression.cjs`: 26/26 passed.
- `node tests/v2-polling-regression.cjs`: 34/34 passed.
- `node tests/review-loading-browser.cjs`: 18/18 passed in production Edge,
  viewport 1440px and 375px. API fixtures hold responses until assertions verify
  that each faster resource is already displayed. Separate 503 cases check
  metadata/report/evidence/audit errors and keyboard Retry, retaining successful
  sections and checking per-endpoint request counts. Initial audit count is 1;
  after Save it is 2. Rapid I1 → list → I2 navigation releases I1 responses while
  I2 is still loading and confirms no old data appears, then loads I2 successfully.

Browser request logs and screenshots are generated in
`frontend/test-results/review-loading/`; `results.json` records scenario results.
The initial navigation fixture omitted required created_at values; it was corrected
before the final successful run. It was not treated as an application defect.

Not verified: live backend/AI, physical mobile devices, real network bandwidth
throttling (controlled delayed API responses were used), development-mode request
counts, or independent checkout without the pending auth integration. Video media
was aborted in this focused fixture; playback was outside this task's scope.

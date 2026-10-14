# Incident status and explicit analysis

Frontend change, 2026-10-12. Scope: V1 ProcessingView; API/backend unchanged.

Opening or reloading an incident never calls POST analyze. Engineers explicitly
choose Start analysis for an unstarted incident or Retry analysis after failure
or cancellation. Pending creation is locked and duplicate clicks are ignored.
The existing `analysis:create` permission controls both the button and handler;
Reviewer/Admin can read status without initiating analysis. Server authorization
remains required.

A saved job ID resumes GET job polling. Terminal jobs stop polling. Successful
jobs load report/evidence; retrying failed output loads never starts analysis.
An unavailable saved job (404) is cleared and incident status is read again.
Without a saved job ID, a PROCESSING incident is followed using GET incident
status until completion/failure. It does not offer another Start button.

API V1 has no read endpoint to discover a job by incident ID. Detailed job progress
in a new tab/device needs an API addition; frontend currently shows incident status
instead. No backend change was performed.

Validation commands:

- `npm run typecheck`, `npm run lint`, `npm run build` (isolated frontend copy).
- `node tests/v2-polling-regression.cjs` (34 tests, fake timers/hooks).
- `node tests/review-draft-regression.cjs` (26 tests, fake hooks/storage).
- `node tests/incident-status-browser.cjs` against a production server on 3102
  (16/16 scenarios passed).

Browser verification uses Edge at 1440px/375px, intercepted API fixtures, delayed
creation and a transient 503. Request logs/screenshots are generated under
`frontend/test-results/incident-status/`. It covers failed/ready reopening and
reload with zero unsolicited analyze requests; explicit Start/Retry; running
job tracking across reload; failed/cancelled terminal jobs; view-only roles;
successful completion and output retry; missing-job-ID status tracking.
This is not live backend/AI integration or a physical mobile-device check.

The working tree contains pre-existing staged auth integration. Existing auth
hooks in the affected files are retained; other auth files are not part of this
change. Validation runs against that working tree. This change depends on those
auth modules; it is not a standalone replacement for the pending auth integration.

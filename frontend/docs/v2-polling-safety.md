# V2 polling recovery — audit item 4

Validated on 2026-10-11. Changes are limited to frontend.

## Behavior

- A serial coordinator owns the timer and AbortController. The next cycle starts only after all three reads settle; concurrent Refresh clicks share the pending cycle.
- Network errors and HTTP 408/429/5xx retry after 2, 4, 8, 16, then at most 30 seconds. A successful cycle resets the delay. Existing data remains visible during failures; the error clears on recovery.
- An authoritative succeeded/failed/cancelled or no-job response stops automatic polling, including when an auxiliary read fails. Other permanent errors stop automatic retries; Refresh can retry explicitly.
- Unmount/recording change clears the timer, aborts reads and active operations, and suppresses late state writes. Mutations and pagination wait for the current polling cycle before starting.

## Actual validation

- Typecheck, lint, production build and git diff --check passed.
- `node frontend/tests/v2-polling-regression.cjs`: 20/20 passed against production source, including lifecycle, backoff, terminal states, partial failures, mutation serialization and request signals.
- `node frontend/tests/review-draft-regression.cjs`: 26/26 passed.
- Browser: independent production build at localhost:3101 using the loopback fixture in `frontend/tests/v2-polling-browser-fixture.cjs`. Desktop viewport 1440×900; mobile viewport 390×844.
- Desktop queued: closing the API listener produced Failed to fetch while retaining queued. Restarting it with running recovered automatically without Refresh and cleared the error.
- Mobile running: closing the listener retained running with the error. Restarting with succeeded recovered automatically and cleared the error. Retry can take up to the current 30-second backoff.
- Terminal job-read counts stayed unchanged across separate 5-second observation windows: succeeded 65→65, failed 66→66, cancelled after reload 68→68. UI showed each corresponding status.
- With 5-second response latency and three rapid Refresh clicks, maximum simultaneous job reads was 1. Completed cycles took approximately 5 seconds, then waited approximately 2 seconds before the next cycle (fixture timestamps: 5681769→5686785, next 5688815→5693830, next 5695855; relative suffixes).
- Navigating through Back to recordings during a pending cycle aborted all three reads. Job-read count stayed 4→4 over 7 seconds after navigation; active jobs 0, maximum 1, aborted requests 3.

Screenshots: [desktop outage](assets/v2-polling-desktop-offline.jpg), [mobile recovery](assets/v2-polling-mobile-recovered.jpg).

## Limits

The browser used synthetic job data and an actual local API connection outage, not a browser-wide offline toggle or the real backend/provider. Real backend end-to-end execution, authentication expiry in browser, and POST actions were not browser-tested; their relevant coordination/error behavior was covered by regression tests. The existing app on port 3000 had a missing Next module, so its server/cache was left untouched. Candidate pagination reset (audit item 5) is outside this task.

No backend or other non-frontend change was needed. Temporary validation servers/build copies were removed after testing.

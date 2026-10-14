# Font and polling measurements — 2026-10-11

Only frontend changes. Measurements used the production Next.js build on Windows, local server `127.0.0.1:3102`, headless Edge 155.0.4283.45, 1440×900, no CPU throttle. Each controlled experiment used three new browser contexts. Existing staged auth changes were present and kept constant in both builds; they are excluded from this task's commit. These are browser measurements with synthetic API responses, not live backend or end-user benchmarks.

Raw measurements: [baseline](font-polling-baseline.json), [final](font-polling-after.json).

## Evidence and changes

The font experiment delayed the Google stylesheet by 1,800ms and returned an empty stylesheet. This isolates CSS render blocking; it does not measure the font binary or typography. Before, the stylesheet was a CSS `@import`. After, `DeferredFont` adds one shared stylesheet link after hydration; the existing system fallback renders while Mulish loads. Median FCP was **1,872ms → 60ms**; samples were 2,184/1,868/1,872ms before and 344/60/56ms after. Median observed LCP was 1,928ms → 136ms on this small fixture page. The delayed CSS still took approximately 1.8 seconds in both builds; the improvement removes its dependency from the initial render, not its download time.

The font query now uses variable weights 400–900 instead of six separate weights, following the [Google Fonts CSS2 axis-range syntax](https://developers.google.com/fonts/docs/css2#axis_ranges). A separate same-client API request comparison returned 30 font-face declarations / 10,926 uncompressed CSS bytes before and 5 declarations / 1,841 bytes after. That API response comparison is not a measurement of total browser-transferred font bytes. An intermediate deferred-load implementation emitted multiple completed fetch events for the same font URL; the final Latin UI run emitted one stylesheet request and one WOFF2 request.

One additional natural Google Fonts run per build confirmed Mulish loaded successfully. FCP was 272ms before and 56ms after; CSS duration was 199ms / 196ms and observed CLS was approximately 0.045 in both. One sample is insufficient to claim a general real-network speedup or a CLS improvement. Cross-origin font resource timing/transfer totals were incomplete; total font bandwidth has not been quantified. Font swap still occurs after initial fallback text. If the stylesheet fails, the system fallback remains usable.

The polling experiment returned jobs in 80ms, candidates in 900ms, and session in 1,200ms. Each trial followed queued → running → succeeded. Before, `RecordingWorkspace` waited for the entire `Promise.allSettled` batch before publishing job state. After, it publishes the job response immediately, guarded by recording lifetime and AbortSignal; the serial coordinator still waits for every sibling response before scheduling another cycle.

Median response-end → job DOM-update delay across nine observations was **1,123ms → 2ms** (after range approximately 1–5ms). This measures DOM publication, not the next screen paint or worker processing speed. Each trial still made three jobs, three candidates and three session requests. Maximum simultaneous requests to the same endpoint was one. No analysis mutation was sent, and no new job poll occurred during the 3.4-second observation after the terminal response. Request count, two-second normal poll interval, retry backoff, session refresh and server permission checks are unchanged; no reduction in polling traffic or backend load is claimed.

## Validation

- `node tests/font-polling-performance.cjs baseline` and `after`: controlled browser measurements and terminal-stop assertions passed.
- `node tests/font-polling-performance.cjs verify`: blocked font stylesheet remained interactive using fallback; queued → HTTP 503 → running → succeeded recovered, cleared its old error, and stopped polling.
- `node tests/v2-polling-regression.cjs`: 31/31 passed, including transient errors, permanent errors, no overlap, abort/unmount, recording rebind, pagination retention and terminal states.
- `node tests/responsive-list-browser.cjs`: production browser checks passed after the loading change at 320/375/768/1024/1440px and equivalent 200% reflow. Native browser-menu zoom remains unverified.
- `npm run typecheck`, `npm run lint`, `npm run build`: passed. Reported shared first-load JS remained 87.3kB at the build output's precision; this is not a bundle-reduction claim.

Run from `frontend`, start `npm run start -- --port 3102`, then run the scripts above. `PERFORMANCE_BASE_URL` and `PERFORMANCE_BROWSER` override the local URL and installed Chromium-family channel. The baseline measurement requires the original source snapshot before this task; do not run `baseline` on the optimized code and treat it as an original result. Existing raw evidence is preserved above. Results do not establish mobile-device performance, real API latency, large-candidate payload costs, background-tab behavior, or production p95 performance.

After the timing runs completed, the shared `.next` cache was overwritten and supplemental browser checks failed with missing server chunks / a missing BUILD_ID. Those failed checks are not performance samples. The final recovery and responsive checks were rerun against an isolated frontend copy with its own production cache on the same port; no other process was stopped or changed. The isolated build also passed. Its local `.env` was excluded; API calls were fulfilled by the same browser fixtures.

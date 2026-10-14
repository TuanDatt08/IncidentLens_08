# V1 upload progress, cancellation and retry

2026-10-12. Frontend-only change to the existing V1 multipart upload. V2 resumable
upload and backend/API contracts are unchanged.

Upload uses XHR upload progress events (loaded/total bytes for the multipart body,
including video, telemetry and multipart overhead). It does not advance by a timer.
If total is unknown, the progress indicator is indeterminate and reports bytes sent.
The upload-body load event changes the status to waiting for server response;
100% bytes sent does not mean that server processing succeeded.

Cookie/CSRF, session-change cancellation and existing auth-expiry events are
preserved in the upload transport. File pickers, drag/drop and Remove are locked
while sending or waiting. A synchronous request ref prevents duplicate submissions,
including stale handlers before React rerenders. Cancel aborts the active XHR,
keeps both selected files and allows another upload. Request identity checks discard
old callbacks/responses after Cancel or unmount. Files also remain selected after
network/API errors. Successful navigation keeps submission locked until unmount.

Checks:

- `npm run typecheck`, `npm run lint`, `npm run build`: passed on an isolated
  frontend copy with BACKEND_INTERNAL_URL set to the local upload fixture.
- `node tests/upload-transport-regression.cjs`: 4/4 passed (byte events, sent
  phase, CSRF/header handling, abort, stale response, session change, 401 and network
  error). This is a fake-XHR fixture, not browser/backend integration.
- `node tests/upload-dropzone-regression.cjs`: 6/6 passed, including existing
  validation/accessibility and new duplicate-submit, lock, retained-file, error,
  cancel/retry and unmount cases with hook/service fixtures.
- `node tests/upload-progress-browser.cjs`: 4/4 passed on production Edge at
  1440px/375px. Actual HTTP multipart requests pass through Next's proxy to a
  local Node fixture on 3112. CDP throttles upload to 256 KiB/s and 1 MiB/s.
  Native intermediate upload progress was observed. Cancel during sending stopped
  both uploads after the fixture received 32,768 bytes; neither body completed.
  Error/success retries each received 2,097,485 multipart bytes with source.mp4,
  log.csv, the fixture cookie and CSRF header. A held response verified the waiting
  status. A 503 kept both files and subsequent retry opened the READY incident.
  Cancel while waiting kept the upload page after the old server response was
  released, with files retained and Create enabled.

Artifacts: `frontend/test-results/upload-progress/results.json`, native XHR
events/server byte counts and screenshots, including `*-waiting-server.png`.

Limits: no live backend/AI, physical mobile device, production proxy or large
2 GB upload was tested. Cancel aborts the browser request; it does not roll back
an incident the server may already have persisted. The working tree includes
pending auth integration; existing auth code in touched files is preserved and
other pending auth files are outside this commit. Integration checks apply to
this working tree, not an independent checkout without the pending auth modules.

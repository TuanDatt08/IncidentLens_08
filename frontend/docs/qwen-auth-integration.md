# Frontend integration on Qwen 7B

Source: `origin/feat/fe-auth` at `8e1dc3b`. Only `frontend/` changes are integrated. API, backend, database, deployment and VLM files are unchanged.

Authentication UI and services are included, but `NEXT_PUBLIC_ENABLE_AUTH` defaults to false. This branch's backend does not provide auth/users endpoints. Enable auth only with a compatible authenticated backend; this flag is a frontend integration option, not server access control.

With auth disabled, the existing API base URL, mock default, business actions and Recordings routes remain available. No session request or login redirect runs. Account management is unavailable. With auth enabled, auth calls use the same-origin `/api/v1` rewrite and retain CSRF/session handling.

The Qwen review-context component and its interpretation of unconfirmed detection remain intact. V1 review uses the existing review-context endpoint instead of the incoming telemetry and analysis-coverage endpoints. The upload offset remains `syncOffset` internally and `sync_offset_s` on the wire. Report and workflow endpoint names and payloads remain unchanged.

Frontend improvements include responsive navigation, independent loading/retry states, upload progress/cancellation, serialized polling, draft recovery, media controls, review tabs and report export. Unsaved edits and in-flight saves block submission; requests are protected against duplicate UI actions.

Run typecheck, lint and build in `frontend/`. Browser checks with intercepted API fixtures verify frontend behavior only; live database, auth and VLM integration require their services.

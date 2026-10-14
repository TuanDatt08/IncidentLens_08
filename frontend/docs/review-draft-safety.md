# Review draft safety — audit items 1, 2, 3 and 11

Date: 2026-10-11. Scope: frontend only. Canonical references: [incident workflow](../../tools/specs/incident-workflow.md), [report versioning](../../tools/adrs/ADR-009-report-versioning-and-audit.md), [frontend integration task](../../tools/tasks/RAV-017-frontend-v2-integration.md).

## Behavior

- V1 shares editor dirty/saving state with workflow. Submit is unavailable before recovery initialization, while edits are unsaved, or while saving. The confirmation handler also checks these conditions.
- V1/V2 lock editing during save/reload. Synchronous in-flight guards suppress duplicate requests. Failed requests and version conflicts retain the local draft.
- Confirmation Cancel, Close, rejection input and Escape cannot dismiss or alter a pending decision. Failed decisions remain visible for retry.
- Unsaved edits prompt before same-tab link navigation. Reload/tab close use the browser's beforeunload prompt. Pending mutations block same-tab navigation until completion.
- Browser Back/Forward is not intercepted with history mutations. Editor changes are copied synchronously to sessionStorage so returning/remounting in the same tab can restore them. Routes are keyed by report/incident ID; stale request completions cannot erase newer recovery copies after unmount.
- Recovery stores editor fields only, never media or full reports, for up to 24 hours in the current tab. Matching versions restore automatically only for editable drafts. Older/read-only recovery is disclosed separately for copying; it does not replace official read-only report text. V1 restoring old edits retains the original PATCH version to trigger server conflict checks; V2 requires copying/discarding the older recovery before editing the latest report.
- V2 recovery keys include the live authorized session subject and report ID. V1 has no principal available in its existing client, so its key is tab/origin plus incident ID. This is not an account-isolation/authentication change.
- Storage denial/quota errors do not crash editing. The UI reports unsuccessful recovery writes/removal. Successful saves/reloads remove recovery where storage permits; failed reloads retain it. Explicit discard requires confirmation.

## Validation evidence

- `npm --prefix frontend run typecheck`: PASS.
- `npm --prefix frontend run lint`: PASS, no warnings/errors.
- `node frontend/tests/review-draft-regression.cjs`: PASS, 26/26 behavioral tests.
- Production build: PASS using `npm --prefix <frontend/.audit-validation> run build` on an identical temporary source copy with the installed node_modules junction. The temporary copy was removed afterward. Direct `npm --prefix frontend run build` was blocked by an existing lock/EPERM on `frontend/.next/trace`; the existing server was not stopped.

The regression suite transpiles actual production modules with TypeScript and executes them using VM/hook/browser-event mocks. It covers slow/deferred saves, duplicate requests, dirty Submit, pending dialog controls/Escape, navigation decisions, recovery remount, version/actor isolation, readonly reports, storage failures/expiry/malformed data, failed reload, successful cleanup and stale response completion. It does not verify real React DOM scheduling, native browser focus/prompts or live API integration.

## Browser coverage still pending

Browser inventory returned no available surfaces; Chrome creation returned `Browser is not available: chrome`. No desktop/mobile walkthrough, real network throttling, browser reload/Back/Forward, focus restoration or native dialog test was executed. Mock tests are not browser/API E2E evidence.

When browser access is restored, verify V1 and V2 on desktop 1440px and mobile 390px (plus narrow 320px):

1. Edit without Save; confirm Submit is blocked; cancel link navigation and remain on the draft.
2. Throttle PATCH/decision requests; confirm fields and Cancel/Close/Escape stay locked; inject failures and retain text/reason.
3. Confirm navigation, then return using Back/Forward; verify recovery. Reload with the browser prompt canceled and accepted; verify restoration when storage is available.
4. Change the server version/status or session actor; verify no silent stale/other-actor restoration and official readonly text remains unchanged.
5. Save, leave and return; verify saved data is used. Resolve an old pending request after leaving and creating newer edits; verify newer recovery remains intact.

No backend/API changes were required. Shared task/backlog files were not changed because the user restricted writes to frontend. Tests are inside frontend for the same reason. Frontend Agents editor, React/accessibility review and regression validation ran; shadcn/Vite-specific gates were not applicable to this existing native Next/React implementation. Impeccable/Ponytail capabilities were not exposed in this session; existing UI patterns and native dialogs were retained.

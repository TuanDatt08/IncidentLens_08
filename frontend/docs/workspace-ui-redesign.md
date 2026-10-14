# Workspace UI redesign — 2026-10-12

User-approved scope: implement the compact incident/report layout, collapsible navigation, tinted indigo/teal palette and role-aware actions. No commit or push.

Related canonical work: [RAV-017](../../tools/tasks/RAV-017-frontend-v2-integration.md), [RAV-014](../../tools/tasks/RAV-014-authentication-rbac.md), [role requirements](../../tools/specs/user-roles.md).

## Behavior

- Sidebar defaults to icons, expands with an accessible toggle and remembers the preference. Mobile uses a wrapping navigation rail; keyboard Escape closes the account menu and restores focus.
- Engineer can create/edit/submit; Reviewer can approve/reject; Admin can read incidents and manage users. Visibility uses existing permissions; backend RBAC remains authoritative. V2 continues using its separate session and reviewer-versus-submitter check.
- Incident list shows actual report review status separately from processing. Completed items read the existing report endpoint, at most four requests in flight. Unfinished processing is never inferred as draft or approved. Unknown/missing/error states are disclosed.
- Search, review counts and filters apply to the loaded page (up to 20 items), explicitly labeled. Global review filtering requires a future list API capability.
- Overview presents evidence beside the report; Evidence uses the full content width; History displays audit. Editors remain mounted to preserve drafts. History pauses media and cancels pending legacy seeks.
- Navy navigation, a blue/lavender canvas, indigo controls and teal accents replace large white areas. Focus, hover, selected states and short transitions include reduced-motion support.

## Validation

- TypeScript, ESLint and isolated production build passed.
- 69 targeted Node regression checks passed: report recovery/workflow, polling/list recovery, upload/filter affordances and review-state request boundaries.
- Browser verification passed: 6 real auth/API tests with SQLite and the isolated fake worker; 4 UI fixture tests for all three roles, actual review labels/filtering, sidebar persistence, menu keyboard behavior, 320/375/768/1440px reflow, reduced motion, tab draft preservation, full-width Evidence and History media pause. Synthetic preview media in the UI test is distinct from real authenticated Range checks.
- Long-identifier responsive regression passed for Incidents and Recordings at 320/375/768/1024/1440px and 200% reflow, with menus open/closed: no root overflow, clipped identifiers, blocked controls or undersized controls.
- Admin form now stays mounted during session expiry: permission availability drops during reauthentication, while AuthProvider hides the form and the server continues enforcing access. Returning as the same actor preserves non-secret fields and clears temporary passwords.
- Reproduce browser checks: `$env:UI_TEST_BROWSER='msedge'; npm run test:e2e`. The existing server's cache lock and missing default Chromium were resolved with isolated caches and installed Edge. Legacy auth test assumptions were updated for explicit Start analysis and the directly editable draft; nonexistent telemetry download assertions were removed.
- Production build uses `$env:NEXT_DIST_DIR='.next/ui-build'; npm run build`. Browser test caches use `.next/ui-e2e`, avoiding the existing dev server's locked trace. `UI_TEST_BROWSER=msedge` selects installed Edge; the default Playwright browser is unchanged.
- Static UX review: no blocking findings after fixing selector mismatches, Evidence width and hidden media playback. Pre-existing V2 report/audit lifetime on route ID changes remains an advisory.

Screenshots use synthetic data: desktop/mobile incident list and report overview were copied to the chat's visualization artifact directory. UI fixture tests regenerate their own PNGs in ignored `test-results/`.

## Video player — 2026-10-12

- Shared player for incident preview and approved V2 evidence clips: visible played/buffered progress, mute/volume, 0.25–2x speed, fullscreen and scoped keyboard shortcuts inspired by YouTube. Controls remain visible and use 44px targets; mobile hides only the volume slider and wraps controls.
- Video uses object-contain and a stage capped at 56dvh/640px; fullscreen fills available space. Actual media duration replaces the former 30-second placeholder. Existing source approval and timestamp conversion remain intact; V2 timestamp seeking preserves paused playback.
- Editor implementation and focused accessibility/React review completed. Review fixes preserve keyboard focus when the central Play overlay disappears and announce Pause immediately during buffering. Build/lint/typecheck and player regression passed; 26 report recovery regression cases passed.
- Installed Edge browser test passed with synthetic range-enabled MP4: seek, speed, fullscreen enter/exit, overlay keyboard focus, input shortcut isolation, History pause, unsaved draft preservation, and no horizontal overflow at 320/375px. V2 shared integration is covered by source/recovery checks, not a new authenticated V2 playback walkthrough.

## Compact review and export preview — 2026-10-12

- Export report is available in both report headers. PDF/DOCX share a readable saved-report preview; JSON previews the exact saved schema. Unsaved edits are explicitly excluded. JSON and genuine OOXML DOCX download directly; PDF uses the browser Print / Save PDF dialog, which supplies paginated print preview. Media attachments are excluded.
- Headers now use an 18px title, compact back/status/export controls and tighter workflow/tabs. From 1024px, equal evidence/report panes scroll independently within the viewport; mobile keeps document scrolling. Explicit max-content grid rows prevent the video from being compressed by the evidence cards. Player controls occupy less height on desktop while retaining 44px touch targets.
- Two bounded editors implemented export/layout and the orchestrator integrated compact player/tests. Focused accessibility/React review found print focus and Word multiline issues; both fixed. Other broad specialist reviews were unnecessary for this bounded change; production build covers type/lint checks.
- Edge fixture verification covers separate mouse-wheel scrolling, video ratio/viewport fit, 1024px Save visibility, saved JSON/DOCX downloads, preview focus/Escape, print content and focus restoration, and 320px preview sizing. Print is stubbed in headless verification; the OS print dialog and actual user-selected PDF saving are manual steps. Downloaded DOCX CRC and Word XML were independently parsed with Python, and the export regression checks Unicode, line breaks, package relationships and escaped print HTML. V2 export normalization and recovery are checked outside browser fixtures.

## Dark palette and calmer typography — 2026-10-12

- Workspace now uses charcoal surfaces, gray-white text and one muted cool accent. Review badges retain subdued semantic colors; login and printable documents keep their existing light context. Export chrome is dark while document paper is light.
- Removed redundant report eyebrows/status and duplicated timeline statistics; softened headings/labels and stacked list editor fields to avoid narrow three-column text wrapping. Timeline markers remain 44px targets with smaller visible dots and always visible times.
- Thin rounded pane scrollbars and slim progress/volume tracks use visible light thumbs. Fine-pointer video seek hitbox remains 24px for compact controls, expanding to 44px with coarse pointers; native keyboard behavior remains intact. WebKit and Firefox slider rules are separate.
- Bounded editor plus accessibility/design review completed. Fixed light hover utilities and translucent pale cards that reduced dark-mode contrast. Four Edge UI fixtures passed across all roles and responsive widths; focused report verification checks the dark background, evidence hover, preview/downloads and pane scrolling. Player/export and 26 report recovery regression checks passed; type/lint/production build passed. No commit or push performed.

## Follow-up polish — 2026-10-12

User feedback: layout and palette were not agreed; some elements looked misaligned and incident navigation required precise clicks on text.

- Replaced lavender/indigo surfaces with a charcoal sidebar, neutral blue-gray canvas and restrained teal accents.
- Removed conflicting shell padding and report grid utilities. One report ratio/gap/breakpoint now controls the split; controls/table columns use aligned padding. Toolbar groups search and processing on the left; counts align right.
- Desktop rows use one native link with an overlay covering the whole row, preserving table semantics, keyboard focus and open-in-new-tab. Mobile cards are complete native links without nested anchors.
- Browser click checks exercised the far-right row padding and bottom-right card padding for Engineer/Reviewer/Admin. Static accessibility/layout review passed. Build (including lint/types) and 34 list/polling regression checks passed. Screenshot evidence uses synthetic data.

## Deferred capabilities

PDF/JSON/DOCX export is not implemented in this layout pass. No placeholder export claims a successful download. No backend contract, role grants or V2 identity integration changes.

## Analysis progress motion — 2026-10-12

- V1 processing and V2 recording analysis share a slim progress component. Reported values interpolate over 1.8 seconds; a subtle sweep is clipped inside the known fill. Unknown totals and queued jobs show activity without a numeric percentage. Only successful jobs reach 100%.
- Failed, cancelled and paused updates stop activity. Reduced-motion preferences disable animation and interpolation. Existing polling, cancellation, retry and role behavior remain intact; no animation timers were introduced.
- Edge browser verification passed queued/unknown progress, interpolated movement, reduced motion, failed and successful states. Production build including lint/types passed; typecheck and all 35 progress/polling regression checks passed after the queued-state correction. No commit or push performed.

## Evidence comparison layout — 2026-10-12

- Evidence tab places video/timeline on the left and evidence/coverage on the right in equal columns at desktop widths (1024px and above), with independent scroll containers. Smaller screens stack the panes. Both V1 and V2 use the same layout; switching tabs preserves mounted video and unsaved report edits.
- Bounded editor and static UX review passed. Edge fixture verified side-by-side geometry, evidence scrolling without moving the media pane, tab changes and retained drafts; existing mobile overview checks also passed. Production build including lint/types and 26 draft recovery regression checks passed. V2 split and mobile Evidence stacking were reviewed in source; browser geometry evidence covers V1 desktop. No commit or push performed.

## Progress counter and typography refinement — 2026-10-12

- Replaced CSS-only interpolation with a shared requestAnimationFrame sequence: visible percentage and fill move together over 1.8 seconds toward each reported value, restarting from the currently displayed value on updates. ARIA exposes the actual reported target. Frame callbacks and motion preference listeners are cleaned up on update/unmount; reduced motion, errors and paused updates snap to the target.
- Reduced the processing page title size, shortened its description and softened progress/status typography. Editor and static review completed; removed render-time reads of animation refs after review feedback.
- Edge fixture passed visible percentage interpolation, synchronized fill, unknown progress, reduced motion, failure and success. Production build including lint/types and all 35 progress/polling regressions passed. No commit or push performed.

## Compact analysis scope and history explanation — 2026-10-12

- Analysis scope shows only frame count/duration and a sampling limitation by default. Native Analysis details contains timestamps and telemetry; Technical notes holds deduplicated diagnostics without removing distinct source information. Unknown coverage remains explicit and does not imply a safe or incident-free video.
- Review history explains its action/actor/time purpose and has a clearer empty state. Existing audit retrieval and events remain unchanged.
- Bounded editor and static review passed; Edge fixture verified collapsed details, keyboard expansion, nested notes and exact duplicate removal while retaining report/player behavior. Production build including lint/types passed. No commit or push performed.

## Telemetry charts synchronized with video — 2026-10-13

- Added a compact signal chart below the video in V1/V2 review. Available log channels can be selected individually; axes retain readable HTML labels on mobile. The chart displays actual sampled values, explicit units, missing-value gaps, the incident window and a playback cursor. Clicking the plot or using its keyboard-accessible timeline seeks without forcing playback.
- Verified video alignment is required for synchronization. V1 uses mapped video seconds directly; V2 converts between recording seconds and the approved clip start, restricting seeks to that clip. Unknown alignment displays the actual log clock with seeking disabled. Missing logs show an empty state; fetch failures have an independent retry and requests abort on identity changes/unmount.
- Additive authenticated read APIs, storage scope, allowlist and bounded sampling are documented in [telemetry API](../../api/docs/telemetry-chart.md). Existing report payloads and role grants remain unchanged.
- Bounded frontend/backend editors and specialist static review completed; addressed mobile axis readability and the Edge native-input keyboard seek issue. Four Edge fixtures passed V1 playback/click/keyboard seeking, mobile layout, unknown/missing telemetry, V2 nonzero clip offsets and existing report interactions. Ten telemetry/API-contract tests and 111 related authorization/clock regressions passed; player regression and 26 draft recovery tests passed. Ruff and typecheck passed. Browser checks use controlled data, not live vehicle logs or live AI validation. No commit or push performed.

## Stable video seeking and pause controls — 2026-10-13

- Removed the buffering text and its state from player controls so seeking does not insert/remove a row or change player geometry. Initial metadata loading is an absolute overlay within the stage. The center Play button changes color on hover without resizing or moving.
- Bounded editor and source review passed. Edge fixture verified unchanged stage/player bounds after waiting, unchanged pause overlay bounds on hover, synchronized chart seeking and mobile flow. Player regressions and typecheck passed. No commit or push performed.

# Galaxy Observatory verification — 13 October 2026

## Final surface polish

Exact isolated production commit-tree verification on port 3106: polish **13/13 passed in one run** at `frontend/.tmp/landing-polish/run-2026-10-13T15-46-19-941Z/`. Public route/interaction checks initially passed **20/22** at `frontend/.tmp/landing-final/run-2026-10-13T15-45-57-985Z/`; two screenshot-preparation checks waited for decorative floating reveal surfaces to stop moving. Screenshot preparation now uses native instant scrolling rather than Playwright's stability gate. Targeted screenshot checks passed **4/4** at `run-2026-10-13T15-48-12-941Z/`, covering all widths. All **22 distinct public checks** pass with this screenshot-only retry; user interaction checks still use normal clicks and route assertions. Full-page/hero screenshots for all four widths are in the targeted capture directory. This verifies the isolated production tree rather than unrelated staged auth integration.

The bounded polish suite verifies pointer-following glow and clearing, overlay click-through, evidence/workflow selection, keyboard focus freeze, offscreen pause, coarse-pointer glow suppression, reduced motion, overflow, root API isolation, and page errors at 1440/375/320 widths.

An initial run found mobile outer-surface animation prevented stable interaction. Outer interactive surfaces now remain stationary on coarse pointers while inner illustrations retain ambient motion. The next full run passed **12/13** at `frontend/.tmp/landing-polish/run-2026-10-13T15-43-51-532Z/`; one 320-pixel selection was clicked before handlers were ready. A targeted hydration-ready normal-click retry passed **1/1** at `run-2026-10-13T15-45-05-093Z/`. All **13 distinct polish checks** pass across these runs; clicks are not forced. Reduced motion also disables pointer glow.

Desktop capability hover lighting and final mobile demo screenshots were inspected: text stays readable and the overlay does not intercept interactions. Glow is low-opacity and does not modify product data. Pointer delegation cleans up RAF and listeners, including media and document-visibility listeners. No planetary renderer changes are part of this polish.

## Follow-up: cosmic satellites and ambient artwork

Public UI passed **22/22** at `frontend/.tmp/landing-final/run-2026-10-13T15-25-14-610Z/`. The expanded motion suite initially passed **25/29** at `frontend/.tmp/galaxy-final/run-2026-10-13T15-25-37-171Z/`. Its three ambient-pause checks initially scrolled to the footer, which could leave the large artwork surface visible, and the desktop handoff checked before smooth scrolling settled. Targeted retries use instant scroll and explicitly assert `data-space-active="false"`: ambient **3/3** passed at `run-2026-10-13T15-30-25-564Z/`; handoff **1/1** passed at `run-2026-10-13T15-30-48-714Z/`. Thus all **29 distinct motion checks** pass with targeted retries; this is not a single 29/29 run.

Six painted, accessibility-hidden decorative satellites are visible on desktop; four on mobile. Over 2.1 seconds, their measured displacement ranged from 44.6–163.1 pixels on desktop, 35.0–53.8 pixels at 375, and 34.2–53.0 pixels at 320. Satellite transforms freeze offscreen and under reduced motion. Workflow and capability artwork moves while visible and stops when its surface is genuinely outside the viewport. Reduced motion disables those ambient animations. No root API requests, page errors, or horizontal overflow were observed; public checks cover 320/375/768/1440 widths.

Desktop/mobile hero phase 3, workflow, capabilities, and mobile full-page screenshots were inspected. Added props create visible cosmic activity; headline, copy, and CTA remain stationary. Decorative crossings can temporarily occlude other decorative panels/core labels, consistent with the existing orbit scene. New hero and artwork images use `WIDTH-satellite-orbit-N.png`, `WIDTH-workflow-ambient.png`, and `WIDTH-capabilities-ambient.png` in the motion directory. Representative handoff images are also in `frontend/docs/assets/galaxy/desktop-space-v3.png` and `mobile-space-v3.png`.

Read-only hook review confirms observers/listeners/RAF cleanup and static satellite placement for reduced motion. If IntersectionObserver is absent, artwork remains static rather than continually rendering. Genuine hidden-tab browser transition and hardware-wide 60 FPS behavior remain unverified; source handles document visibility and capped rendering.

## Follow-up: realistic illustrative dashcam and orbit refinement

Final public landing checks passed **22/22** at `frontend/.tmp/landing-final/run-2026-10-13T15-10-25-137Z/`. Final Galaxy checks passed **23/23** at `frontend/.tmp/galaxy-final/run-2026-10-13T15-10-29-228Z/`. These checks cover the local photographic illustration and new camera-facing orbital panels; auth was not rerun because auth implementation did not change.

All three panels moved significantly over 3.1 seconds: desktop displacement 155.0 / 125.0 / 135.6 pixels; 375-pixel touch viewport 53.3 / 91.5 / 74.3 pixels; 320-pixel touch viewport 51.2 / 90.8 / 66.7 pixels. The local AI-generated dashcam image loaded successfully, panel bounds stayed inside the scene at tested phases, and panels did not overlap the hero headline. Offscreen panel transforms stop changing; reduced-motion panel transforms remain static.

Each viewport has six `WIDTH-satellite-orbit-0.png` through `WIDTH-satellite-orbit-5.png` captures at approximately three-second intervals. This samples about half of the 32-second orbit, plus the initial displacement interval. Desktop and mobile phase 0/3 images were visually inspected: the planet remains visible, CTA/text stay stationary, and satellite movement is obvious. On mobile some decorative panels/core labels temporarily overlap during crossings; this does not obscure product interactions or the hero copy. Full-page and hero captures are in the public-check directory.

Read-only React/accessibility inspection found matching cleanup for observers, resize observers, media listeners, visibility listeners, timers, and animation frames. Orbit elapsed time pauses offscreen; reduced motion restores static CSS positions. Decorative scene semantics provide a Vietnamese descriptive name and the illustrative photograph is explicitly identified as AI-generated rather than real incident footage. No new interaction was introduced inside the decorative orbital panels. Measurements remain headless development evidence, not a hardware-wide smoothness guarantee.

Rendered Microsoft Edge headless checks use synthetic landing data and mocked auth/incident responses. They do not verify a live backend or VLM.

## Results

- Public landing/workspace checks: 22/22 passed at 1440, 768, 375, and 320 CSS pixels. Covers root API isolation, evidence buttons, CTA navigation, keyboard menu/focus, reduced motion, no-JavaScript fallback, and fixture workspace.
- Auth-enabled checks: 2/2 passed on the targeted final retry. Public root makes no auth API request; anonymous workspace CTA reaches login; authenticated CTA reaches workspace. Earlier development runs encountered cold compilation and an obsolete heading assertion; the heading assertion now checks the semantic `lp-title` element, and navigation allows 30 seconds for development compilation.
- Galaxy checks: 20/20 passed. Includes actual frame changes, touch/coarse-pointer contexts, render pixel caps, four workflow stages, scroll handoff progression and clipping, offscreen render pause, forced unavailable WebGL fallback, reduced motion, and API isolation.

## Actual motion observations

Desktop canvas counter advanced 46 to 102 between screenshot captures. At 375 pixels it advanced 19 to 47; at 320 pixels, 21 to 45. Three-second live sampling recorded 72 desktop changes (median interval 41.6 ms, maximum 83.4 ms), 51 touch-mobile changes at 375 (median 55.6 ms, maximum 97 ms), and 52 at 320 (median 55.6 ms, maximum 69.5 ms). Mobile device DPR was 2 while render DPR stayed 1. Six desktop sequence PNGs show changing core/particle positions with stable text and panels.

These are intentionally capped render updates measured under headless development load. They establish actual animation and expose occasional longer gaps; they do not establish a universally smooth frame rate or hardware GPU performance. Hidden-tab behavior was reviewed in source but no genuine hidden-tab transition was asserted in this browser run.

Hero headline/body computed contrast against the quiet deep-space background is 18.71:1 / 9.87:1. White CTA text against its actual default gradient endpoints is 4.96:1 / 6.17:1. Background glow still requires visual review; computed solid-background values alone are insufficient for gradients.

At 320 pixels, the handoff section is 356.42 pixels tall and the final label bottom is 316.42 pixels inside it; at mobile widths all measured heading, copy, and label bounds remain inside the clipped section. Forced WebGL-unavailable and reduced-motion screenshots preserve the designed fallback and product content.

## Persistent artifacts

- Public/full-page set: `frontend/.tmp/landing-final/run-2026-10-13T15-01-50-190Z/` — `1440-hero.png`, `1440-full.png`, `375-hero.png`, `375-full.png`, `320-full.png`, reduced-motion/no-JavaScript screenshots, and fixture workspace. Its JSON records 23/24 because the anonymous login route exceeded the initial five-second development timeout.
- Final targeted auth retry: `frontend/.tmp/landing-final/run-2026-10-13T15-03-22-858Z/` — `results.json`, `auth-login-fixture.png`, `auth-workspace-fixture.png` (2/2 passed).
- Final Galaxy set: `frontend/.tmp/galaxy-final/run-2026-10-13T14-57-26-330Z/` — `results.json`, `1440-frame-a.png` / `1440-frame-b.png`, mobile frame pairs, `motion-sequence-0.png` through `motion-sequence-5.png`, handoff captures, `webgl-fallback.png`, and `reduced-motion.png` (20/20 passed).

Artifacts live outside `test-results` to prevent other Playwright suites from removing them. Representative desktop/mobile images were also copied into `frontend/docs/assets/galaxy/` for handoff.

# IncidentLens landing page

## Direction and scope

Cinematic promise: video, telemetry and evidence become one inspectable incident story, with engineers making the final review.

Public route `/` replaces the former redirect to `/incidents`. Only exactly `/` bypasses the existing AuthProvider/workspace shell. Every business route keeps the existing session and permission handling. Primary CTA links to `/incidents`; workflow CTA links to `#quy-trinh`. Backend/VLM/services/contracts are outside this change.

Midnight optical analysis lab: near-black navy (#070b16), cyan (#78edff), violet (#a897ff), white (#edf3ff), muted cool blue (#a3afc5). Large, tightly tracked system/Mulish typography already supported by the application; monospace labels. An asymmetric first viewport balances a compact story against an evidence-convergence sculpture. Use wide spacing, thin technical borders and restrained luminous edges. Semantic warm tones indicate human review.

Type: headline clamp 42–78px, section headings 32–52px, body 16–18px, technical labels 11–12px. Spacing: 8px base, sections 96–128px desktop/64–80px mobile; 1200–1320px content width. Interactive targets at least 44px. Corners are modest for controls and larger only for product surfaces.

## Technology and states

Cinematic ladder rung 5: inline SVG, CSS depth and pointer response. Static images or fixed video cannot express linked, selectable evidence; WebGL would add unnecessary runtime cost for this constrained scene. No new dependency, no external assets, no particle loop or API data. Server-rendered vectors provide a complete fallback with JavaScript disabled, WebGL unavailable, offline fonts or reduced motion. Pointer response is capped and only active with a fine pointer and motion enabled. Ambient transform/opacity animations pause offscreen/when the tab is hidden. IntersectionObserver is progressive enhancement, never a requirement for readable content.

Scene structure: synthetic road-video source, cyan telemetry waveform, evidence points, connected paths and optical core. Demo uses selected event buttons with aria-pressed, a synthetic video diagram and telemetry cursor sharing explicit **seconds from the start of the demo video**; no conversion from real V1/V2 timestamps. All numeric demo values are labelled fabricated. No real incident/video/customer data is used.

Navigation: native disclosure menu on mobile, Escape closes and returns focus; section activation closes the menu. Normal anchors work without JS. Sticky navigation changes background on scroll. Desktop split hero becomes stacked on mobile. Demo changes from video + inspector to stacked surfaces; no fixed-width scrolling layout. Focus rings, text contrast, visible selection, semantic headings, keyboard-first controls and reduced-motion fallbacks are required.

Content: MP4 upload, optional CSV/explicit alignment, analysis status, evidence/video review, editable draft, version/conflict handling and submit/review workflow are confirmed in current source. Do not claim accuracy, latency, exhaustive coverage, autonomous safety decisions, certification or unsupported privacy guarantees.

## Verification

Run typecheck, lint and production build. Browser checks: 1440/768/375/320px, hero visual nonblank, no overflow, disclosure keyboard/Escape, primary CTA retains route auth behavior, workflow anchor, demo selection and announced timestamp, reduced motion, JS-disabled content, no landing API requests or browser exceptions. Capture and inspect desktop/mobile images. Fixture checks are frontend checks, not live API/VLM E2E.

`tools/` and dedicated Impeccable/Ponytail instructions are absent in this checkout. Existing frontend AGENTS, product implementation/API docs and actual code are used instead; older implementation docs contain acknowledged stale gaps, so capability claims are checked against current source.

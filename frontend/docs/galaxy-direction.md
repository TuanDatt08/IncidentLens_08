# Galaxy Observatory

## Design contract

The analysis core is an observatory for incident data: video, optional telemetry and derived evidence converge, then the engineer inspects and reviews the result. The layout changes from a flat technical diagram to a large luminous scene beside a two-line editorial headline, floating glass navigation and consistent deep-space sections.

Landing-only palette: deep space `#050611`, midnight indigo `#10132B`, violet `#8B5CF6`, electric cyan `#22D3EE`, sparse magenta `#E879F9`, cold white `#F4F6FF`, muted text `#AFB4D1`. Glow stays primarily behind the scene, not the reading column. Typography and CTA remain legible before enhancement. The existing SVG road scene is synthetic, not real footage.

## Technology choice

Cinematic ladder rung 7, narrowly scoped: one dependency-free WebGL fragment pass analytically shades a plasma sphere and projected orbit rings with depth cues, procedural nebula and sparse data lights. The upgrade explicitly calls for a living galaxy core with inclined orbits; the prior CSS rings cannot express moving surface material and front/back orbit shading as clearly. No Three.js, R3F, ray-marched scene, bloom pipeline or external asset is added. Normal React 18 / Next 14 components supply all content and controls.

The canvas is dynamically imported only when the scene is near the viewport and motion is permitted. Shader/asset loading failure, unavailable WebGL, save-data/low-core devices and reduced motion retain an always-present SVG/CSS scene. The fallback also covers JavaScript disabled. Import failures resolve to the fallback; shader compile/link and context loss do not start a broken loop. After context loss the static scene remains active.

Renderer cost is bounded: one canvas/pass, three analytic orbits, three noise octaves, no texture downloads or postprocessing, width cap 960px, DPR at most 1.25 desktop/1 coarse-pointer, draw cap 30 desktop/20 coarse-pointer. These are limits, not measured performance claims. Rendering pauses offscreen and on document visibility changes; its time advances only while active.

## Composition and interaction

- Floating dark-glass navigation, preserved native mobile disclosure and Escape/focus behavior.
- Quiet headline column next to a dominant core, larger diagonal orbital field and three smaller data panels. Pointer response affects only decorative atmosphere, capped at 2–2.5 degrees; text and panels remain stationary.
- Fixed one-viewport distant stars, near stars and soft nebula layers provide page continuity without giant composited page-sized animated layers. CSS animation pauses when the document is hidden.
- Short natural-scroll handoff between core and evidence; scroll updates a bounded CSS progress variable, with static mobile/reduced-motion presentation. No wheel/touch interception, cursor replacement or scroll hijacking.
- Observatory product console: original synthetic selectable evidence, explicit demo clock, clear telemetry and human-review context.
- Four selectable workflow stages on a connected signal track, with distinct upload, core, evidence and report illustrations. Keyboard supports Tab/Enter plus Left/Right/Home/End. Selection is presentation-only and performs no business action.
- Varied capability surfaces and galaxy-halo final CTA, with valid links only.

All route/auth/API/BE/VLM behavior is outside this upgrade. `/` remains public, primary CTA remains `/incidents`, workflow CTA remains `#quy-trinh`. Product claims and demo timestamp semantics from the first landing remain unchanged. Concurrent alternate landing files were saved under `.tmp/galaxy-concurrent-snapshot/` after the user explicitly chose to continue this Galaxy implementation; unrelated `globals.css` changes were preserved.

## Verification contract

Run typecheck/lint/build, rendered desktop/tablet/mobile/320px checks, both auth fixture scenarios, actual frame changes, frame-count progression, offscreen pause, forced missing WebGL, reduced motion, no-JavaScript fallback, workflow selection, handoff scroll progress, focus, overflow and representative contrast. Screenshots at multiple animation times must be inspected; changing frames alone do not prove smooth frame times or GPU performance. Tests remain frontend fixtures, not live API/VLM integration.

# Landing page verification

## Delivered surface

Public `/`: Vietnamese navigation, asymmetric cinematic hero, optical convergence scene, interactive synthetic review demo, four-step workflow, confirmed capabilities, final CTA and footer. Primary links go to `/incidents`, preserving the existing authentication guard. Workflow links target `#quy-trinh` and transfer focus to that section.

Main sources: `app/page.tsx`, `app/landing.css`, `components/landing/landing-page.tsx`, `landing-visuals.tsx`, `landing-demo.tsx`. The only workspace integration change is the exact `/` exception in `components/auth/auth-provider.tsx`. Business services, payloads, existing workspace screens, backend and VLM are unchanged by this landing implementation. Next adds its verification-cache type path to `tsconfig.json` during build.

## UI verification decisions

- Visual direction: midnight optical lab, cyan signal paths and violet analysis rings; actual vector road scene rather than a placeholder gradient.
- Layout: desktop split hero, tablet stack, mobile rearranged scene and stacked inspector; all sections use scoped landing styles.
- Content: telemetry explicitly optional; engineers verify and review AI drafts. No performance, accuracy, customer or security-certification claims.
- Privacy: all road imagery, values, evidence and incident IDs are fabricated and labelled Demo minh họa. Landing performs no incident/auth API requests.
- Time: synthetic ten-second video clock; event positions derive from `time / duration`. Signal markers and values share that clock. Real V1/V2 timestamps are untouched.
- Accessibility: native mobile disclosure, Escape/focus restoration, semantic headings, button pressed states, live inspector update, focus rings and anchored section focus. Technical demo labels were increased after screenshot inspection.
- Motion: capped pointer response, slow optical orbits and signal flow, short readable intro/reveals. Scene animation pauses offscreen/hidden; reduced motion disables animations and pending pointer updates. Inline SVG and anchors remain usable without WebGL or JavaScript.
- Routing: public root does not mount workspace/auth logic. Guard behavior on `/incidents` remains unchanged in both anonymous and authenticated fixture checks.

## Commands and evidence

Final result: typecheck, lint and production build passed; 81 regression tests passed; 24/24 rendered Edge checks passed. Desktop/mobile screenshots were inspected. Final browser artifacts: `test-results/landing/run-2026-10-13T14-26-13-001Z/results.json` and screenshots in the same directory.

`npm run typecheck`, `npm run lint`, `npm run build` and the existing upload, draft, V2 polling and media regression suites are used. The regression run contains 81 passing tests. Build uses `NEXT_DIST_DIR=.next/landing-build` to avoid corrupting a running development server's cache.

`node tests/landing-browser.cjs` verifies 1440/768/375/320px, evidence interaction, section CTA/focus, mobile keyboard menu, API isolation, reduced motion, no-JavaScript rendering and workspace navigation with synthetic fixtures. Set `LANDING_BASE_URL` to the running default frontend and optionally `LANDING_AUTH_BASE_URL` to a separate frontend with `NEXT_PUBLIC_ENABLE_AUTH=true` for guard checks. Artifacts are saved into a unique `test-results/landing/run-*` directory with `results.json` to avoid Windows image-preview overwrite locks.

An editor subagent implemented bounded landing CSS; a product/React/accessibility reviewer checked content, routing and cleanup and ran rendered verification. Main agent inspected screenshots and fixed history-state preservation, reduced-motion rAF cleanup, intro/reveal motion and label readability. Vite/shadcn-specific reviewers are not applicable to this existing Next 14/React 18 project without shadcn/Radix dependencies.

## Limits

Browser API/session fixtures verify frontend behavior only. They do not establish live database/auth/VLM integration. Existing backend limitations remain outside this change. `tools/` and dedicated Impeccable/Ponytail instructions are absent; current source and available frontend guidance were used. No hosting/public deployment or new dependency is introduced.

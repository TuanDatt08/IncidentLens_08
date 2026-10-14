# Shared theme and interaction verification

The landing Galaxy palette (cyan actions, violet identity) now supplies fixed light/dark tokens for landing, auth and workspace. The color editor was replaced with a theme toggle; selection persists in localStorage and synchronizes across tabs. An early initialization script avoids a wrong-theme flash on reload.

Routes use a 220ms opacity transition without remounting children. Reduced-motion changes cancel the transition. Native wheel scrolling is preserved, anchor scrolling is smooth, and mobile report layout uses document scrolling instead of a fixed-height nested scroll area. Interactive controls have hover, keyboard focus, pressed and disabled feedback.

Validation on 2026-10-14: typecheck, lint and production build passed. Playwright with Edge and intercepted API fixtures verified /, /login, /incidents, /incidents/new, /recordings, /admin/users, /change-password and /recordings/REC-FIXTURE in light/dark at widths 1440, 768, 390 and 320. No horizontal document overflow or JavaScript page errors; theme persistence, reduced-motion scroll behavior and client navigation passed. Screenshots: frontend/.tmp/theme-motion/. This is UI fixture verification, not live backend E2E. Incident/report review pages are not included in this browser matrix.

Frontend production workflow delegated route animation and CSS risk review to motion_review. Existing Next/React components were retained. Fancy UI design guidance was reviewed; a gallery redesign or package installation was unnecessary because the user specified the existing landing palette. No new animation dependency was added.

Run the browser checks with a server on http://127.0.0.1:3101: node tests/theme-motion-browser.cjs.

Live preview follow-up: created demo@example.com in the isolated auth-workspace SQLite database with engineer/reviewer/admin roles. Frontend localhost:3101 proxies to the real API on 127.0.0.1:8002. Browser verified actual cookie login, incident listing, QA-STRUCTURED review loading, media playback/pause, timeline seek, Inspect/Report/History tabs and light mode. QA-STRUCTURED is explicitly a UI fixture, not a Qwen result. Report saving/submission and new upload were not tested in this walkthrough. Screenshot: docs/assets/demo-account-review-light.png.

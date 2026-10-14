# Galaxy workspace and authentication integration

The workspace now follows the active `landing-galaxy` palette in `app/galaxy.css`: background #050611, cyan #22d3ee, violet #8b5cf6, text #f4f6ff, muted #afb4d1. Primary actions use the landing's violet gradient. Workspace/auth share Mulish and LensMark. The public landing remains accessible without a session.

Backend authentication is selectively integrated from `origin/feat/auth`, preserving the current Qwen and V2 implementations. V1 uses server-side permission checks, session cookies and CSRF. Auth and V2 migrations have an additive merge revision. V2 continues to use its independent identity system and is disabled in this local auth preview.

## Local preview

Run `.venv/Scripts/python.exe -m backend.cli.auth_preview --port 8001` at repository root, then run `npm run dev -- --hostname 127.0.0.1 --port 3000` in `frontend`. The ignored frontend `.env.local` enables auth, disables mock data and points the rewrite at port 8001.

The preview uses a separate `.tmp/auth-workspace/preview.db` and storage directory. It seeds branch fixture accounts `operator@example.com` (Engineer), `reviewer@example.com` (Reviewer), and `admin@example.com` (Admin), with password `cD4!yz`. These are local preview accounts, not production credentials. No Qwen worker is started by the preview script.

## Verification

- Frontend typecheck, lint and production build passed.
- Python Ruff passed for API/backend and preview script.
- Browser: Operator login, authenticated incident listing, logout, Admin login and real user directory verified.
- Login desktop screenshot: `assets/auth-galaxy-login.png`.
- API/auth test results are reported in the accompanying backend integration documentation.

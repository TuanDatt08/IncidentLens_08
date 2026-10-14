# Internal auth integration with Qwen / V2

The backend now includes the internal authentication implementation from `origin/feat/auth`: Argon2id passwords, opaque HttpOnly cookie sessions, CSRF + exact Origin checks, session expiry/revocation, forced password changes, shared login throttling, administrator user management, explicit engineer/reviewer/admin permissions, and self-review prevention.

V1 API routes (including new diagnostics and review-context routes) require a verified session. V1 mutations record the authenticated account in audit history. Landing remains public on the frontend. V2 retains its existing signed local identity contract and remains separate from cookie auth.

The auth migration preserves its original revision parent. The additive `20261014_auth_v2` merge joins it with the existing V2 jobs head, so `alembic upgrade head` has a single head and preserves both historical paths. Qwen worker and inference code are unchanged.

## Local preview

Run from repository root:

```powershell
.venv/Scripts/python.exe -m backend.cli.auth_preview --port 8001
```

This uses `.tmp/auth-workspace/preview.db` and its own storage, applies migrations, and creates these local preview accounts if absent:

- `operator@example.com`: engineer
- `reviewer@example.com`: reviewer
- `admin@example.com`: admin

All use the auth branch fixture password `cD4!yz`, with no forced password change for preview. These are isolated development accounts, never production defaults. No worker or fake analysis is started. Use `--prepare-only` to apply migrations and seed without launching a server.

For existing deployed databases, run migrations and bootstrap an administrator with the hidden-password CLI:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m backend.cli.users create-admin --email your@email.example --name Administrator
```

The local dataset CLI now requires `--actor-email` for an active engineer account, so incident creation/analysis remains auditable. Production requires secure cookies and exact HTTPS CORS origins as specified by the auth branch.

## Verification

Run the API and auth domain tests with:

```powershell
.venv/Scripts/python.exe -m pytest tests/api tests/backend/test_auth_domain.py --basetemp=.tmp/auth-checks -q
```

Windows sandbox socketpair initialization can hang before async tests start. Use the authorized host execution environment for this test command if that happens. PostgreSQL concurrency tests require a dedicated disposable `auth_test` database via `AUTH_TEST_POSTGRES_URL`; SQLite tests do not establish PostgreSQL concurrency guarantees.

### Verified on 2026-10-14

- Combined API + auth domain + optional PostgreSQL suite: **172 passed, 4 skipped**, with one initial generated OpenAPI pin mismatch (819.24 seconds). PostgreSQL cases skipped because no dedicated `AUTH_TEST_POSTGRES_URL` was supplied.
- The exporter includes all API component schemas. Added auth contracts (`ChangePassword`, `CreateUser`, `Login`, `ResetPassword`, `UpdateUser`) changed the generated pin; all V2 paths and all existing component definitions were verified identical before regenerating with `python -m api.export_v2_contract`.
- Focused rerun of the pin comparison and HTTPException / rate-limit header regressions: **3 passed** (0.19 seconds).
- Ruff passed for the integrated production files and focused tests. Qwen worker/inference code was not changed by this integration; existing dirty pipeline modifications were preserved.

The tests ran against isolated databases. They do not establish live Qwen inference quality or PostgreSQL concurrent locking behavior. Preview browser verification and deployment checks are documented separately by the frontend workflow.

# RAV18 backend runbook

## Start

From the repository root, set `OPENAI_API_KEY` for real analysis and run `docker compose up --build`. Compose starts PostgreSQL, applies Alembic migrations, then starts the API at `http://localhost:8000` and a separate analysis worker. Uploads and evidence persist in `data/incidents`; PostgreSQL data persists in the `postgres_data` volume. `GET /api/v1/health` checks that the API process is responding.

For database-only development, run `docker compose up -d postgres`, then `docker compose run --rm --no-deps backend alembic upgrade head`. PostgreSQL listens on `127.0.0.1:5432` with the local demo database/user `rav18`; the API and worker remain stopped. Docker Compose mounts the named volume `p-076_postgres_data`, so restarting the container preserves data.

The OpenAPI description is available at `http://localhost:8000/docs`; upload, analyze, job polling, and report reads publish response schemas there.

The `DATABASE_URL` default targets a local PostgreSQL instance. Tests use a temporary SQLite database and a fake VLM. To run them, install `requirements.txt` and `requirements-dev.txt`, then run `python -m pytest tests/ -q`. To inspect PostgreSQL migration SQL without a server, use `python -m alembic upgrade head --sql`.

For a PostgreSQL and FFmpeg smoke test, create a separate database with `docker compose exec -T postgres psql -U rav18 -d postgres -c "CREATE DATABASE rav18_e2e;"`, migrate it with `docker compose run --rm --no-deps -e DATABASE_URL=postgresql+psycopg2://rav18:rav18@postgres:5432/rav18_e2e backend alembic upgrade head`, then run `docker compose run --rm --no-deps -e DATABASE_URL=postgresql+psycopg2://rav18:rav18@postgres:5432/rav18_e2e -e INCIDENT_STORAGE_DIR=/tmp/rav18-e2e-storage -e RAV18_PG_E2E=1 backend pytest -q tests/postgres_smoke.py`. The test generates an MP4 with FFmpeg and uses a fake VLM. It refuses to run against the main `rav18` database.

## API sequence

1. `POST /api/v1/incidents/upload` with multipart `video` and optional `log`; save `incident_id`.
2. `POST /api/v1/incidents/{incident_id}/analyze`; save `job_id` from the 202 response.
3. Poll `GET /api/v1/jobs/{job_id}` until `succeeded`, `failed`, or `cancelled`. On success, fetch `result_uri` and `GET /api/v1/incidents/{incident_id}/evidence`.
4. Read `GET /api/v1/incidents/{incident_id}/audit` for the event trail.

The frontend branch currently expects an SSE progress route and a different payload. Its build can pass while runtime integration fails; see [backend-contract-v1.1.md](backend-contract-v1.1.md) for exact changes needed in its service layer.

The review write routes are available in local development/test. PATCH requires the current report `version` and only accepts `summary`, `timeline`, `key_factors`, `observations`, and `unknowns`. Submit, approve, and reject follow `DRAFT → IN_REVIEW → APPROVED/REJECTED`; reject requires a nonblank `reason`. Review writes and media routes return 403 in production until real authentication and role checks are integrated.

For local browser playback, use `GET /api/v1/incidents/{incident_id}/video` and `GET /api/v1/incidents/{incident_id}/evidence/{evidence_id}/media`. These routes support byte ranges. Evidence `uri` remains an internal relative storage path. To seek to an evidence timestamp in the source MP4, add the incident's `video_metadata.collision_offset_in_video_s` to its collision-relative `time_range_s`.

Local development accepts browser origins `http://localhost:3000` and `http://127.0.0.1:3000` alongside `CORS_ORIGINS`. Production uses only the configured origins.

## Open contract decisions

The API final v1.1 marked review PATCH whitelist, reject-reason requirement, role enforcement, video retention, CARLA ingress, and polling ETag as `NEED_CONFIRMATION`. The user has confirmed the PATCH whitelist, required reject reason, local demo without role checks, media route, and a successful empty report when no incident is found. Role enforcement, video retention, CARLA ingress, ETag, list/audit pagination, and reopening a rejected report remain open. Evidence URIs stay internal.

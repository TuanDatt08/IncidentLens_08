# RAV18 backend runbook

## Start

From the repository root, set `OPENAI_API_KEY` for real analysis and run `docker compose up --build`. Compose starts PostgreSQL, applies Alembic migrations, then starts the API at `http://localhost:8000` and a separate analysis worker. Uploads and evidence persist in `data/incidents`; PostgreSQL data persists in the `postgres_data` volume. `GET /api/v1/health` checks that the API process is responding.

The `DATABASE_URL` default targets a local PostgreSQL instance. Tests use a temporary SQLite database and a fake VLM. To run them, install `requirements.txt` and `requirements-dev.txt`, then run `python -m pytest tests/ -q`. To inspect PostgreSQL migration SQL without a server, use `python -m alembic upgrade head --sql`.

## API sequence

1. `POST /api/v1/incidents/upload` with multipart `video` and optional `log`; save `incident_id`.
2. `POST /api/v1/incidents/{incident_id}/analyze`; save `job_id` from the 202 response.
3. Poll `GET /api/v1/jobs/{job_id}` until `succeeded`, `failed`, or `cancelled`. On success, fetch `result_uri` and `GET /api/v1/incidents/{incident_id}/evidence`.
4. Read `GET /api/v1/incidents/{incident_id}/audit` for the event trail.

The frontend branch currently expects an SSE progress route and a different payload. Its build can pass while runtime integration fails; see [backend-contract-v1.1.md](backend-contract-v1.1.md) for exact changes needed in its service layer.

The review write routes are pending the v1.1 decisions described below. The current API can be exercised through report/evidence reads and audit, but cannot complete an approval workflow yet.

## Open contract decisions

The API final v1.1 marks review PATCH whitelist, reject-reason requirement, role enforcement, video retention, CARLA ingress, and polling ETag as `NEED_CONFIRMATION`. Browser video/evidence access (media route or signed URL), no-incident outcome, and how a rejected report resumes editing also affect the unfinished public contract. Evidence URIs are deliberately internal until access is specified. `collision_offset_in_video_s` in video metadata is the MP4 seek origin for collision-relative evidence timestamps.

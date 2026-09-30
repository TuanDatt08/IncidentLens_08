# RAV18 backend MVP

The FastAPI service exposes `/api/v1` for incident upload, analysis jobs, reports, evidence, and audit events. PostgreSQL is the metadata store. Local incident storage holds uploaded MP4 files, canonical telemetry CSV, and generated evidence assets. The API and worker share that storage. See [the v1.1 contract notes](docs/backend-contract-v1.1.md) for public fields and unresolved decisions.

## Flow

1. `POST /incidents/upload` saves and validates an MP4 and optional CSV, normalizes telemetry to `sec_from_incident`, and inserts an `Incident` with `processing_status=READY`.
2. `POST /incidents/{incident_id}/analyze` inserts a persistent `Job` and returns its `job_id`. The frontend polls `GET /jobs/{job_id}`.
3. The worker leases a queued job from PostgreSQL. Pass 1 samples frames to decide whether an incident is visible and locate it in the MP4. Pass 2 inspects a clip, keyframes, and the aligned telemetry window. A fake VLM is injected in tests.
4. Successful processing writes evidence files, their hashes and relative URIs, an initial `AnalysisReport`, `ReportVersion` 1, and audit events in one database transaction. The report is separate from the factual `IncidentRecord`.

The six tables are `incidents`, `jobs`, `evidences`, `analysis_reports`, `report_versions`, and `audit_events`. Alembic creates them. Job status (`queued/running/succeeded/failed/cancelled`), incident processing status (`UPLOADED/READY/PROCESSING/COMPLETED/FAILED`), and report review status (`DRAFT/IN_REVIEW/APPROVED/REJECTED`) have separate meanings.

Evidence `time_range_s` and report `incident_window` are seconds relative to the incident, so they can be negative. The worker uses the internal `collision_offset_in_video_s` to convert to MP4 time. Evidence URIs are storage paths, not public media URLs. Local demo media routes serve the source video and incident-owned evidence with HTTP Range; they return 403 in production until real authentication is integrated.

## Runtime

`docker compose up --build` starts PostgreSQL, runs the Alembic migration, then starts the API and worker. Provide `OPENAI_API_KEY` for real VLM processing. The API itself can accept and list incidents without a model key. `DATABASE_URL`, `INCIDENT_STORAGE_DIR`, and the model settings are environment variables. Do not expose the incident storage directory as an unauthenticated static mount.

See [docs/backend-runbook.md](docs/backend-runbook.md) for local commands and the current integration limits.




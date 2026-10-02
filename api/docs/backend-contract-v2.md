# API contract V2

[Pinned OpenAPI](openapi-v2.json) · [Implementation](../../backend/docs/v2-implementation.md). Namespace `/api/v2`; V1 giữ nguyên. All V2 operations authenticate signed principal and recording scope; no role header is trusted. Production identity/storage integration is gated.

| Resource | Operations | Contract |
| --- | --- | --- |
| session | GET | subject, roles; no identity secret/token returned |
| recordings | GET | scoped list, cursor, limit 1–200 |
| recordings/{id}/candidates | GET | multiple candidate windows in video_seconds, reasons, analysis_state, optional report_id |
| recordings/{id}/analyze | POST | provider_profile, Idempotency-Key; 202 returns persistent job ID; no GET triggers inference |
| recordings/{id}/jobs | GET | latest durable job; recover after reload/new browser |
| jobs/{id} | GET | status/stage/attempt/coverage/budget/partial_results/sanitized error |
| jobs/{id}/cancel, /resume | POST | Engineer; cancel retains partial results; resume only failed jobs with attempts left |
| uploads | POST | recording_id, filename, bytes, media_type, sha256, bounded part_size |
| uploads/{id} | GET | verified existing part checksums and expiry; same owner/scope |
| uploads/{id}/parts/{number} | PUT | streamed bytes, X-Part-SHA256; corrupt/oversize fail |
| uploads/{id}/complete | POST | complete hash, MP4 signature, ffprobe; replay idempotent |
| reports/{id} | GET/PATCH | typed AnalysisV2 envelope, immutable read; PATCH expected_version and editable fields |
| reports/{id}/submit, /approve, /reject, /reopen | POST | expected_version; reject reason required; Reviewer differs from submitter |
| reports/{id}/versions, /audit | GET | ordered immutable snapshots, signed actor/action/reason/time |
| reports/{id}/evidence | GET | scoped IDs/time/source/privacy/media URL; no filesystem paths |
| recordings/{id}/evidence/{evidence_id}/media | GET | MASKED/PASSED plus stored hash/root checks; RAW denied |

401 missing/invalid session; 403 role/self-review/privacy; 404 scope-safe missing; 409 stale version/active analysis/expired upload; 422 invalid schema/evidence/part; 429 budget; 503 unconfigured production adapter. Cookie mutations additionally require `X-Requested-With: IncidentLens`. Browser client retains edits after 409 and explicitly reloads latest data.

Envelope lists use `{items, next_cursor}`; report fields include recording_id, candidate_id, report_id, version, analysis, provenance and submitted_by. Frame timestamps are absolute video_seconds; clip playback seek is `timeline.time_s - clip.start_s`. Legacy incident-relative v1 seconds are never recast silently.

Tests pin routes/schema plus real HTTP review/upload/jobs fixtures. OpenAPI currently retains shared component schemas and some generic list responses; exact runtime envelope assertions and FE types supply those contracts. Regenerate snapshot when deliberately changing public API, then run contract/regression tests before FE acceptance.

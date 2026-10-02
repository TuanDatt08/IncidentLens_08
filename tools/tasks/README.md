# Task index

Dùng một namespace RAV-NNN. Task liên kết SPEC + ADR + sprint + dependencies; chưa giao owner. Dependency graph theo IDs trong mỗi task; task ở sprint khác vẫn phải hoàn thành prerequisite trước.

- [RAV-001 — Analysis schema V2](RAV-001-analysis-schema-v2.md) — DONE (local AC)
- [RAV-002 — Log normalization](RAV-002-log-normalization.md) — DONE (local AC)
- [RAV-003 — Candidate detection](RAV-003-candidate-detection.md) — DONE (local AC)
- [RAV-004 — Clip and ordered frame extraction](RAV-004-clip-extraction.md) — DONE (local AC)
- [RAV-005 — Anonymization and privacy gate](RAV-005-anonymization.md) — PARTIAL
- [RAV-006 — VLM provider contract](RAV-006-vlm-adapter.md) — DONE (local AC)
- [RAV-007 — External VLM baseline](RAV-007-external-vlm.md) — PARTIAL
- [RAV-008 — Self-hosted VLM baseline](RAV-008-self-hosted-vlm.md) — DONE (local AC)
- [RAV-009 — Evidence validation](RAV-009-evidence-validation.md) — DONE (local AC)
- [RAV-010 — Engineer → Reviewer workflow](RAV-010-review-workflow.md) — DONE (local AC)
- [RAV-011 — Resumable large-media upload](RAV-011-large-media-upload.md) — PARTIAL
- [RAV-012 — Timestamp synchronization](RAV-012-timestamp-synchronization.md) — DONE (local AC)
- [RAV-013 — Immutable report versions and audit](RAV-013-report-versioning-audit.md) — DONE (local AC)
- [RAV-014 — Authentication and RBAC](RAV-014-authentication-rbac.md) — PARTIAL
- [RAV-015 — Job checkpoints, resume and budgets](RAV-015-job-resume-budget.md) — PARTIAL
- [RAV-016 — API V2 and compatibility](RAV-016-api-v2-migration.md) — DONE (local AC)
- [RAV-017 — Frontend V2 integration](RAV-017-frontend-v2-integration.md) — DONE (local AC)
- [RAV-018 — Expert dataset and protocol](RAV-018-expert-benchmark.md) — PARTIAL
- [RAV-019 — Provider quality and cost comparison](RAV-019-provider-cost-comparison.md) — BLOCKED
- [RAV-020 — Observability and release hardening](RAV-020-observability-runbook.md) — PARTIAL

Role indexes: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md). Xem [audit](../docs/implementation-audit.md) cho source/test evidence từng task.

Verified 2026-10-03: 12 DONE (local AC), 7 PARTIAL, 1 BLOCKED. Production gates và remote CI/merge vẫn pending; [execution evidence](../docs/task-execution-2026-10-03.md).

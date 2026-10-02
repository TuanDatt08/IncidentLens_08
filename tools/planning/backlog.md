# IncidentLens capability backlog

Snapshot 2026-10-03. Baseline path đã kiểm source; test result ở [baseline evidence](../docs/baseline-evidence.md). Không lấy số test cũ trong README làm bằng chứng quality AI.

## Baseline đã có

| Capability | Status | Evidence / limitation |
| --- | --- | --- |
| Python contract/demo workflow tested | DONE | Xem baseline test run; scope fake VLM/SQLite, không production AI |
| FastAPI, PostgreSQL models/migrations, worker | PARTIAL | Có source/CI, chưa PG/live deployment verified lượt này |
| Next.js UI | PARTIAL | Có v1 polling/version/seek; audit shape/render còn thiếu, mock default; browser E2E chưa verified |
| Frontend static/build checks | DONE | Typecheck + lint + production build pass; không chứng minh browser integration hoặc AI quality |
| Clip/Range, edit version/audit | PARTIAL | Có source/tests, chưa privacy/auth/transition snapshots V2 |

## MVP work items

| Task | Status | Sprint | Dependencies |
| --- | --- | --- | --- |
| [RAV-001](../tasks/RAV-001-analysis-schema-v2.md) Analysis schema V2 | DONE (local AC) | 01 | — |
| [RAV-002](../tasks/RAV-002-log-normalization.md) Log normalization | PARTIAL | 01 | — |
| [RAV-003](../tasks/RAV-003-candidate-detection.md) Candidate detection | TODO | 02 | [RAV-002](../tasks/RAV-002-log-normalization.md), [RAV-012](../tasks/RAV-012-timestamp-synchronization.md) |
| [RAV-004](../tasks/RAV-004-clip-extraction.md) Clip and ordered frame extraction | PARTIAL | 02 | [RAV-003](../tasks/RAV-003-candidate-detection.md) |
| [RAV-005](../tasks/RAV-005-anonymization.md) Anonymization and privacy gate | TODO | 02 | [RAV-004](../tasks/RAV-004-clip-extraction.md) |
| [RAV-006](../tasks/RAV-006-vlm-adapter.md) VLM provider contract | PARTIAL | 03 | [RAV-001](../tasks/RAV-001-analysis-schema-v2.md), [RAV-004](../tasks/RAV-004-clip-extraction.md) |
| [RAV-007](../tasks/RAV-007-external-vlm.md) External VLM baseline | PARTIAL | 03 | [RAV-005](../tasks/RAV-005-anonymization.md), [RAV-006](../tasks/RAV-006-vlm-adapter.md), [RAV-009](../tasks/RAV-009-evidence-validation.md) |
| [RAV-008](../tasks/RAV-008-self-hosted-vlm.md) Self-hosted VLM baseline | TODO | 03 | [RAV-006](../tasks/RAV-006-vlm-adapter.md), [RAV-009](../tasks/RAV-009-evidence-validation.md) |
| [RAV-009](../tasks/RAV-009-evidence-validation.md) Evidence validation | PARTIAL | 03 | [RAV-001](../tasks/RAV-001-analysis-schema-v2.md), [RAV-004](../tasks/RAV-004-clip-extraction.md) |
| [RAV-010](../tasks/RAV-010-review-workflow.md) Engineer → Reviewer workflow | PARTIAL | 04 | [RAV-009](../tasks/RAV-009-evidence-validation.md), [RAV-013](../tasks/RAV-013-report-versioning-audit.md), [RAV-014](../tasks/RAV-014-authentication-rbac.md), [RAV-016](../tasks/RAV-016-api-v2-migration.md) |
| [RAV-011](../tasks/RAV-011-large-media-upload.md) Resumable large-media upload | TODO | 01 | — |
| [RAV-012](../tasks/RAV-012-timestamp-synchronization.md) Timestamp synchronization | PARTIAL | 01 | [RAV-002](../tasks/RAV-002-log-normalization.md) |
| [RAV-013](../tasks/RAV-013-report-versioning-audit.md) Immutable report versions and audit | PARTIAL | 04 | [RAV-001](../tasks/RAV-001-analysis-schema-v2.md), [RAV-014](../tasks/RAV-014-authentication-rbac.md) |
| [RAV-014](../tasks/RAV-014-authentication-rbac.md) Authentication and RBAC | TODO | 04 | — |
| [RAV-015](../tasks/RAV-015-job-resume-budget.md) Job checkpoints, resume and budgets | PARTIAL | 02 | [RAV-003](../tasks/RAV-003-candidate-detection.md), [RAV-004](../tasks/RAV-004-clip-extraction.md) |
| [RAV-016](../tasks/RAV-016-api-v2-migration.md) API V2 and compatibility | TODO | 03 | [RAV-001](../tasks/RAV-001-analysis-schema-v2.md) |
| [RAV-017](../tasks/RAV-017-frontend-v2-integration.md) Frontend V2 integration | PARTIAL | 04 | [RAV-010](../tasks/RAV-010-review-workflow.md), [RAV-011](../tasks/RAV-011-large-media-upload.md), [RAV-016](../tasks/RAV-016-api-v2-migration.md) |
| [RAV-018](../tasks/RAV-018-expert-benchmark.md) Expert dataset and protocol | TODO | 05 | — |
| [RAV-019](../tasks/RAV-019-provider-cost-comparison.md) Provider quality and cost comparison | BLOCKED | 05 | [RAV-007](../tasks/RAV-007-external-vlm.md), [RAV-008](../tasks/RAV-008-self-hosted-vlm.md), [RAV-018](../tasks/RAV-018-expert-benchmark.md), [RAV-020](../tasks/RAV-020-observability-runbook.md) |
| [RAV-020](../tasks/RAV-020-observability-runbook.md) Observability and release hardening | PARTIAL | 05 | [RAV-015](../tasks/RAV-015-job-resume-budget.md) |

## Open decisions/resources

- ADR-006: owner cung cấp deployment/retention/region/capacity và chọn storage sau upload prototype/cost comparison. Chỉ production adapter của RAV-011 BLOCKED; contract/mock/dev có thể làm.
- Inference deployment: đủ dataset/threshold/API policy/GPU mới đo và chọn provider. RAV-019 BLOCKED.
- Identity provider: owner xác định issuer/claims/session; role behavior đã chốt, provider integration review trước production.
- Release thresholds/retention/resource budgets: ký trước production benchmark, không suy từ guide template.

## Delivery state

RAV-001 được người dùng chọn triển khai trong Sprint 01 Active; implementation/AC local DONE, delivery chưa PR/CI/merge. Các task còn lại Refined với tentative sprint; chưa hoàn tất chỉ vì schema đã có. Coverage hiện có giữ riêng khỏi delivery state.

## Audit cập nhật và role ownership

[Audit implementation](../docs/implementation-audit.md) baseline: 11 PARTIAL, 8 TODO, 1 BLOCKED. Sau RAV-001: 1 DONE (local AC), 11 PARTIAL, 7 TODO, 1 BLOCKED. External API RAV-007 PARTIAL vì adapter v1 đã có; privacy/V2 chưa đạt. Role folders/doc ownership: [repository roles](../docs/repository-roles.md). Role work-items dẫn về task canonical, không tạo backlog thứ hai.

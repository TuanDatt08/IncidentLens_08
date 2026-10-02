# Sprint 04 — review-workflow

Status: **Active — local verification; production/CI gates pending**

Owner/capacity/dates: chưa giao/chốt.

> For agentic workers: dùng superpowers:executing-plans để thực hiện task đã sẵn sàng; chưa tự dispatch agent hay triển khai task code khi chưa có instruction tương ứng.

Goal: Auth, snapshot và human review trên UI.

Architecture: deterministic preprocessing → evidence → VLM → validators → HITL. Giữ FastAPI/Next.js/PostgreSQL/worker hiện có; implementation mới nằm trong root code, governance trong tools.

Spec: [requirements](../../specs/functional-requirements.md), [NFR](../../specs/non-functional-requirements.md).

## Global constraints

API v1.1 giữ compatibility; external chỉ MASKED/PASSED; AI chỉ DRAFT; snapshot approved bất biến; schema 2.0 video_seconds; provider/storage chưa được tự chốt.

## Review focus

Crash/replay/stale lease (RAV-015); timestamp drift/thiếu anchors (RAV-012); privacy detector failure (RAV-005); cross-incident evidence (RAV-009); self-approve/stale version (RAV-010/014). Acceptance của các task liên quan pin từng failure, không bỏ vì không có happy-path demo.

## Work items

- [x] [RAV-010](../../tasks/RAV-010-review-workflow.md) — Engineer → Reviewer workflow; prerequisite: [RAV-009](../../tasks/RAV-009-evidence-validation.md), [RAV-013](../../tasks/RAV-013-report-versioning-audit.md), [RAV-014](../../tasks/RAV-014-authentication-rbac.md), [RAV-016](../../tasks/RAV-016-api-v2-migration.md).
- [x] [RAV-013](../../tasks/RAV-013-report-versioning-audit.md) — Immutable report versions and audit; prerequisite: [RAV-001](../../tasks/RAV-001-analysis-schema-v2.md), [RAV-014](../../tasks/RAV-014-authentication-rbac.md).
- [ ] [RAV-014](../../tasks/RAV-014-authentication-rbac.md) — Authentication and RBAC; prerequisite: decision gates trong task.
- [x] [RAV-017](../../tasks/RAV-017-frontend-v2-integration.md) — Frontend V2 integration; prerequisite: [RAV-010](../../tasks/RAV-010-review-workflow.md), [RAV-011](../../tasks/RAV-011-large-media-upload.md), [RAV-016](../../tasks/RAV-016-api-v2-migration.md).

## Exit gate

Các work item đạt acceptance/DoD hoặc blocker được giữ và công bố; không đánh dấu sprint complete khi P0 chưa đạt. Test/CI evidence được ghi theo task. Mỗi task là một đơn vị có thể review riêng; thứ tự trong sprint tuân dependency, không chỉ thứ tự số ID. Không chạy external/GPU benchmark nếu chưa có policy/resource.

Checkbox work items = local AC verified, chưa production/remote CI/merge. Xem [current execution evidence](../../docs/task-execution-2026-10-03.md).

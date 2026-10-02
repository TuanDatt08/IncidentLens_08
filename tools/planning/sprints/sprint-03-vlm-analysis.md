# Sprint 03 — vlm-analysis

Status: **Active — local verification; production/CI gates pending**

Owner/capacity/dates: chưa giao/chốt.

> For agentic workers: dùng superpowers:executing-plans để thực hiện task đã sẵn sàng; chưa tự dispatch agent hay triển khai task code khi chưa có instruction tương ứng.

Goal: Provider chung, hai baseline và public V2.

Architecture: deterministic preprocessing → evidence → VLM → validators → HITL. Giữ FastAPI/Next.js/PostgreSQL/worker hiện có; implementation mới nằm trong root code, governance trong tools.

Spec: [requirements](../../specs/functional-requirements.md), [NFR](../../specs/non-functional-requirements.md).

## Global constraints

API v1.1 giữ compatibility; external chỉ MASKED/PASSED; AI chỉ DRAFT; snapshot approved bất biến; schema 2.0 video_seconds; provider/storage chưa được tự chốt.

## Review focus

Crash/replay/stale lease (RAV-015); timestamp drift/thiếu anchors (RAV-012); privacy detector failure (RAV-005); cross-incident evidence (RAV-009); self-approve/stale version (RAV-010/014). Acceptance của các task liên quan pin từng failure, không bỏ vì không có happy-path demo.

## Work items

- [x] [RAV-006](../../tasks/RAV-006-vlm-adapter.md) — VLM provider contract; prerequisite: [RAV-001](../../tasks/RAV-001-analysis-schema-v2.md), [RAV-004](../../tasks/RAV-004-clip-extraction.md).
- [ ] [RAV-007](../../tasks/RAV-007-external-vlm.md) — External VLM baseline; prerequisite: [RAV-005](../../tasks/RAV-005-anonymization.md), [RAV-006](../../tasks/RAV-006-vlm-adapter.md), [RAV-009](../../tasks/RAV-009-evidence-validation.md).
- [x] [RAV-008](../../tasks/RAV-008-self-hosted-vlm.md) — Self-hosted VLM baseline; prerequisite: [RAV-006](../../tasks/RAV-006-vlm-adapter.md), [RAV-009](../../tasks/RAV-009-evidence-validation.md).
- [x] [RAV-009](../../tasks/RAV-009-evidence-validation.md) — Evidence validation; prerequisite: [RAV-001](../../tasks/RAV-001-analysis-schema-v2.md), [RAV-004](../../tasks/RAV-004-clip-extraction.md).
- [x] [RAV-016](../../tasks/RAV-016-api-v2-migration.md) — API V2 and compatibility; prerequisite: [RAV-001](../../tasks/RAV-001-analysis-schema-v2.md).

## Exit gate

Các work item đạt acceptance/DoD hoặc blocker được giữ và công bố; không đánh dấu sprint complete khi P0 chưa đạt. Test/CI evidence được ghi theo task. Mỗi task là một đơn vị có thể review riêng; thứ tự trong sprint tuân dependency, không chỉ thứ tự số ID. Không chạy external/GPU benchmark nếu chưa có policy/resource.

Checkbox work items = local AC verified, chưa production/remote CI/merge. Xem [current execution evidence](../../docs/task-execution-2026-10-03.md).

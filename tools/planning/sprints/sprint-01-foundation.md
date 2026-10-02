# Sprint 01 — foundation

Status: **Active — local verification; production/CI gates pending** (RAV-001 được người dùng yêu cầu thực hiện; các task khác chưa hoàn tất)

Owner/capacity/dates: chưa giao/chốt.

> For agentic workers: dùng superpowers:executing-plans để thực hiện task đã sẵn sàng; chưa tự dispatch agent hay triển khai task code khi chưa có instruction tương ứng.

Goal: Schema/time/upload contract làm nền V2.

Architecture: deterministic preprocessing → evidence → VLM → validators → HITL. Giữ FastAPI/Next.js/PostgreSQL/worker hiện có; implementation mới nằm trong root code, governance trong tools.

Spec: [requirements](../../specs/functional-requirements.md), [NFR](../../specs/non-functional-requirements.md).

## Global constraints

API v1.1 giữ compatibility; external chỉ MASKED/PASSED; AI chỉ DRAFT; snapshot approved bất biến; schema 2.0 video_seconds; provider/storage chưa được tự chốt.

## Review focus

Crash/replay/stale lease (RAV-015); timestamp drift/thiếu anchors (RAV-012); privacy detector failure (RAV-005); cross-incident evidence (RAV-009); self-approve/stale version (RAV-010/014). Acceptance của các task liên quan pin từng failure, không bỏ vì không có happy-path demo.

## Work items

- [x] [RAV-001](../../tasks/RAV-001-analysis-schema-v2.md) — Implementation/AC local verified; remote CI/merge pending.
- [x] [RAV-002](../../tasks/RAV-002-log-normalization.md) — Log normalization; prerequisite: decision gates trong task.
- [ ] [RAV-011](../../tasks/RAV-011-large-media-upload.md) — Resumable large-media upload; prerequisite: decision gates trong task.
- [x] [RAV-012](../../tasks/RAV-012-timestamp-synchronization.md) — Timestamp synchronization; prerequisite: [RAV-002](../../tasks/RAV-002-log-normalization.md).

## Exit gate

Các work item đạt acceptance/DoD hoặc blocker được giữ và công bố; không đánh dấu sprint complete khi P0 chưa đạt. Test/CI evidence được ghi theo task. Mỗi task là một đơn vị có thể review riêng; thứ tự trong sprint tuân dependency, không chỉ thứ tự số ID. Không chạy external/GPU benchmark nếu chưa có policy/resource.

Checkbox work items = local AC verified, chưa production/remote CI/merge. Xem [current execution evidence](../../docs/task-execution-2026-10-03.md).

# Sprint 05 — evaluation-hardening

Status: **Planned**

Owner/capacity/dates: chưa giao/chốt.

> For agentic workers: dùng superpowers:executing-plans để thực hiện task đã sẵn sàng; chưa tự dispatch agent hay triển khai task code khi chưa có instruction tương ứng.

Goal: Expert benchmark, cost comparison và release hardening.

Architecture: deterministic preprocessing → evidence → VLM → validators → HITL. Giữ FastAPI/Next.js/PostgreSQL/worker hiện có; implementation mới nằm trong root code, governance trong tools.

Spec: [requirements](../../specs/functional-requirements.md), [NFR](../../specs/non-functional-requirements.md).

## Global constraints

API v1.1 giữ compatibility; external chỉ MASKED/PASSED; AI chỉ DRAFT; snapshot approved bất biến; schema 2.0 video_seconds; provider/storage chưa được tự chốt.

## Review focus

Crash/replay/stale lease (RAV-015); timestamp drift/thiếu anchors (RAV-012); privacy detector failure (RAV-005); cross-incident evidence (RAV-009); self-approve/stale version (RAV-010/014). Acceptance của các task liên quan pin từng failure, không bỏ vì không có happy-path demo.

## Work items

- [ ] [RAV-018](../../tasks/RAV-018-expert-benchmark.md) — Expert dataset and protocol; prerequisite: decision gates trong task.
- [ ] [RAV-019](../../tasks/RAV-019-provider-cost-comparison.md) — Provider quality and cost comparison; prerequisite: [RAV-007](../../tasks/RAV-007-external-vlm.md), [RAV-008](../../tasks/RAV-008-self-hosted-vlm.md), [RAV-018](../../tasks/RAV-018-expert-benchmark.md), [RAV-020](../../tasks/RAV-020-observability-runbook.md).
- [ ] [RAV-020](../../tasks/RAV-020-observability-runbook.md) — Observability and release hardening; prerequisite: [RAV-015](../../tasks/RAV-015-job-resume-budget.md).

## Exit gate

Các work item đạt acceptance/DoD hoặc blocker được giữ và công bố; không đánh dấu sprint complete khi P0 chưa đạt. Test/CI evidence được ghi theo task. Mỗi task là một đơn vị có thể review riêng; thứ tự trong sprint tuân dependency, không chỉ thứ tự số ID. Không chạy external/GPU benchmark nếu chưa có policy/resource.

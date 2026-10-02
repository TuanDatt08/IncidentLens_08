# Sprint 02 — incident-detection

Status: **Planned**

Owner/capacity/dates: chưa giao/chốt.

> For agentic workers: dùng superpowers:executing-plans để thực hiện task đã sẵn sàng; chưa tự dispatch agent hay triển khai task code khi chưa có instruction tương ứng.

Goal: Candidate đa cửa sổ, evidence/privacy và resume.

Architecture: deterministic preprocessing → evidence → VLM → validators → HITL. Giữ FastAPI/Next.js/PostgreSQL/worker hiện có; implementation mới nằm trong root code, governance trong tools.

Spec: [requirements](../../specs/functional-requirements.md), [NFR](../../specs/non-functional-requirements.md).

## Global constraints

API v1.1 giữ compatibility; external chỉ MASKED/PASSED; AI chỉ DRAFT; snapshot approved bất biến; schema 2.0 video_seconds; provider/storage chưa được tự chốt.

## Review focus

Crash/replay/stale lease (RAV-015); timestamp drift/thiếu anchors (RAV-012); privacy detector failure (RAV-005); cross-incident evidence (RAV-009); self-approve/stale version (RAV-010/014). Acceptance của các task liên quan pin từng failure, không bỏ vì không có happy-path demo.

## Work items

- [ ] [RAV-003](../../tasks/RAV-003-candidate-detection.md) — Candidate detection; prerequisite: [RAV-002](../../tasks/RAV-002-log-normalization.md), [RAV-012](../../tasks/RAV-012-timestamp-synchronization.md).
- [ ] [RAV-004](../../tasks/RAV-004-clip-extraction.md) — Clip and ordered frame extraction; prerequisite: [RAV-003](../../tasks/RAV-003-candidate-detection.md).
- [ ] [RAV-005](../../tasks/RAV-005-anonymization.md) — Anonymization and privacy gate; prerequisite: [RAV-004](../../tasks/RAV-004-clip-extraction.md).
- [ ] [RAV-015](../../tasks/RAV-015-job-resume-budget.md) — Job checkpoints, resume and budgets; prerequisite: [RAV-003](../../tasks/RAV-003-candidate-detection.md), [RAV-004](../../tasks/RAV-004-clip-extraction.md).

## Exit gate

Các work item đạt acceptance/DoD hoặc blocker được giữ và công bố; không đánh dấu sprint complete khi P0 chưa đạt. Test/CI evidence được ghi theo task. Mỗi task là một đơn vị có thể review riêng; thứ tự trong sprint tuân dependency, không chỉ thứ tự số ID. Không chạy external/GPU benchmark nếu chưa có policy/resource.

# RAV-008 — Self-hosted VLM baseline

Status: **TODO**

Delivery Status: **Todo**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P1

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 03](../planning/sprints/sprint-03-vlm-analysis.md)

## Goal

Hoàn thành capability **Self-hosted VLM baseline** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-AI-002](../specs/incident-analysis-v2.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-004](../adrs/ADR-004-vlm-provider-abstraction.md), [ADR-007](../adrs/ADR-007-privacy-before-external-inference.md), [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md), [ADR-010](../adrs/ADR-010-ai-evaluation-strategy.md).

Dependencies: [RAV-006](RAV-006-vlm-adapter.md), [RAV-009](RAV-009-evidence-validation.md).

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

SelfHostedVLMProvider theo RAV-006.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/self_hosted_vlm.py.

Test: `tests/backend/test_services/test_self_hosted_vlm.py`.

## Acceptance criteria

- [ ] Contract test với endpoint fake.
- [ ] model/revision configurable.
- [ ] endpoint nội bộ.
- [ ] context/frame limit.
- [ ] disconnect/timeout bounded.
- [ ] real GPU throughput ghi NOT_MEASURED tới khi có hardware.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_self_hosted_vlm.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

Không self-host adapter/runtime config. Còn thiếu: Internal endpoint adapter, model revision/GPU benchmark. Source: [config.py](../../backend/config.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

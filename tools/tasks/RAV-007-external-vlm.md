# RAV-007 — External VLM baseline

Status: **PARTIAL**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 03](../planning/sprints/sprint-03-vlm-analysis.md)

## Goal

Hoàn thành capability **External VLM baseline** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-AI-002](../specs/incident-analysis-v2.md), [REQ-PRV-001](../specs/security-privacy.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-004](../adrs/ADR-004-vlm-provider-abstraction.md), [ADR-007](../adrs/ADR-007-privacy-before-external-inference.md), [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md), [ADR-010](../adrs/ADR-010-ai-evaluation-strategy.md).

Dependencies: [RAV-005](RAV-005-anonymization.md), [RAV-006](RAV-006-vlm-adapter.md), [RAV-009](RAV-009-evidence-validation.md).

## Background / baseline evidence

`backend/services/vlm.py` đã có OpenAIVLMAdapter gửi keyframe/telemetry với structured output hai pass và mocked contract test. PARTIAL vì chưa privacy gate/allowlist, AnalysisV2 và provenance/cost; chưa live-provider benchmark. Dependency chưa đạt nghĩa là chưa ready cho scope V2.

## Scope and interfaces

ExternalVLMProvider theo interface RAV-006.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/external_vlm.py.

Test: `tests/backend/test_services/test_external_vlm.py`.

## Acceptance criteria

- [x] Mock network chứng minh chỉ MASKED/PASSED + telemetry allowlist.
- [x] endpoint policy.
- [x] schema/time/evidence invalid không persist.
- [x] usage/retry/cost đủ.
- [ ] live smoke chỉ sau egress approval.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_external_vlm.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Mock external transport kiểm MASKED/PASSED, sanitized allowlist, endpoint egress policy, schema/evidence validation và usage. Cost chưa đo để null, retry tổng cost NOT_MEASURED. Live egress approval/smoke và privacy prerequisite chưa có.

Evidence: [test_vlm_provider.py](../../tests/backend/test_services/test_vlm_provider.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

External OpenAI keyframe inference đã có và mocked contract test. Còn thiếu: Privacy/allowlist/V2/evidence checks; chưa live benchmark. Source: [vlm.py](../../backend/services/vlm.py). Test fixture: [test_vlm.py](../../tests/backend/test_services/test_vlm.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

# RAV-009 — Evidence validation

Status: **PARTIAL**

Delivery Status: **Todo**

Technical lead: Backend; phối hợp: API.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 03](../planning/sprints/sprint-03-vlm-analysis.md)

## Goal

Hoàn thành capability **Evidence validation** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-EVD-001](../specs/incident-analysis-v2.md), [REQ-EVD-002](../specs/incident-analysis-v2.md).

ADR: [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md).

Dependencies: [RAV-001](RAV-001-analysis-schema-v2.md), [RAV-004](RAV-004-clip-extraction.md).

## Background / baseline evidence

`backend/models/contracts.py`: bounds/asset validation hiện có; chưa per-claim evidence semantic check. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

validate_analysis(analysis, registry, duration) -> ValidationResult.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/evidence_validation.py; backend/services/review.py.

Test: `tests/backend/test_services/test_evidence_validation.py`.

## Acceptance criteria

- [ ] ID sai/cross incident/time ngoài window/source sai bị chặn.
- [ ] OBSERVED và SUPPORTED_INFERENCE cần evidence.
- [ ] generation/edit/approve dùng cùng validator.
- [ ] unknown không bị ép thành fact.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_evidence_validation.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

EvidenceV1 path/hash/size/window asset checks có. Còn thiếu: Per-claim ID/time/source/cross scope semantic gate trong edit/approve. Source: [reports.py](../../backend/services/reports.py). Test fixture: [test_results.py](../../tests/api/test_results.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

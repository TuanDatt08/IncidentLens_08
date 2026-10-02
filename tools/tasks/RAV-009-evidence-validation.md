# RAV-009 — Evidence validation

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

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

- [x] ID sai/cross incident/time ngoài window/source sai bị chặn.
- [x] OBSERVED và SUPPORTED_INFERENCE cần evidence.
- [x] generation/edit/approve dùng cùng validator.
- [x] unknown không bị ép thành fact.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_evidence_validation.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Shared generation/edit/approval gate kiểm scope/hash/time/source/evidence; unknown giữ nguyên, internal claims không được nâng thành fact thiếu telemetry.

Evidence: [test_evidence_validation.py](../../tests/backend/test_services/test_evidence_validation.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

EvidenceV1 path/hash/size/window asset checks có. Còn thiếu: Per-claim ID/time/source/cross scope semantic gate trong edit/approve. Source: [reports.py](../../backend/services/reports.py). Test fixture: [test_results.py](../../tests/api/test_results.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

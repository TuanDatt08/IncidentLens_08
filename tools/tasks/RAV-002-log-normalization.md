# RAV-002 — Log normalization

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 01](../planning/sprints/sprint-01-foundation.md)

## Goal

Hoàn thành capability **Log normalization** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-SYNC-001](../specs/incident-workflow.md), [REQ-ING-001](../specs/api-contracts.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md).

Dependencies: không có task prerequisite; kiểm tra decision gates bên dưới.

## Background / baseline evidence

`backend/services/telemetry.py`: CSV sec_from_incident streaming/strict; chưa có ROS2/epoch/unit normalization. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

normalize_log(path, format, config) -> NormalizedTelemetry.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/telemetry.py; backend/services/log_normalization.py.

Test: `tests/backend/test_services/test_telemetry.py`.

## Acceptance criteria

- [x] CSV legacy còn đọc được.
- [x] epoch/relative time/unit rõ.
- [x] timestamp lỗi không bị sửa âm thầm.
- [x] ROS2 topic allowlist đọc streaming hoặc báo unsupported rõ.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_telemetry.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: CSV streaming/legacy, explicit epoch/relative/unit, Decimal origin, malformed/order rejection; ROS2 báo unsupported, không thêm dependency.

Evidence: [test_log_normalization.py](../../tests/backend/test_services/test_log_normalization.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Active CSV parser streaming, clock strict. Legacy pandas path không được API gọi. Còn thiếu: ROS2/epoch/unit/signals normalization. Source: [telemetry.py](../../backend/services/telemetry.py). Test fixture: [test_telemetry.py](../../tests/backend/test_services/test_telemetry.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

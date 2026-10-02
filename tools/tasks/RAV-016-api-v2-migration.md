# RAV-016 — API V2 and compatibility

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: API; phối hợp: Backend.

Role docs: [API](../../api/docs/work-items.md), [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 03](../planning/sprints/sprint-03-vlm-analysis.md)

## Goal

Hoàn thành capability **API V2 and compatibility** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-API-001](../specs/api-contracts.md).

ADR: [ADR-005](../adrs/ADR-005-versioned-api-migration.md), [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md).

Dependencies: [RAV-001](RAV-001-analysis-schema-v2.md).

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

OpenAPI v2 + fixture envelopes/expected_version/errors.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): api/v2.py; backend/models/contracts_v2.py; api/main.py.

Test: `tests/api/test_contracts_v2.py`.

## Acceptance criteria

- [x] V2 tách namespace/schema.
- [x] recording có nhiều candidates.
- [x] fixtures pinned trước FE.
- [x] tất cả v1 contract regression pass.
- [x] không đổi time basis v1.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/api/test_contracts_v2.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Namespace/schema V2 additive, multiple candidates, pinned api/docs/openapi-v2.json và HTTP fixtures; V1 contract suite/time basis giữ nguyên. Snapshot pin trước final FE acceptance; initial frontend implementation đã bắt đầu trước snapshot export.

Evidence: [test_openapi_v2.py](../../tests/api/test_openapi_v2.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Public routes chỉ /api/v1. Còn thiếu: Separate V2 schemas/OpenAPI/fixtures, regression giữ v1. Source: [main.py](../../api/main.py). Test fixture: [test_contracts.py](../../tests/api/test_contracts.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

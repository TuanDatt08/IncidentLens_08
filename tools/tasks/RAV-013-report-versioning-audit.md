# RAV-013 — Immutable report versions and audit

Status: **PARTIAL**

Delivery Status: **Todo**

Technical lead: Backend; phối hợp: API.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 04](../planning/sprints/sprint-04-review-workflow.md)

## Goal

Hoàn thành capability **Immutable report versions and audit** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-AUD-001](../specs/non-functional-requirements.md), [REQ-AUD-002](../specs/non-functional-requirements.md).

ADR: [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md), [ADR-009](../adrs/ADR-009-report-versioning-and-audit.md).

Dependencies: [RAV-001](RAV-001-analysis-schema-v2.md), [RAV-014](RAV-014-authentication-rbac.md).

## Background / baseline evidence

`backend/services/review.py`, `models/tables.py`: edit snapshots/audit; transitions chưa new snapshot, actor demo. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

save_snapshot(report, expected_version, actor) -> VersionEnvelope.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/models/tables.py; backend/services/review.py; backend/services/reports.py; backend/alembic/versions/.

Test: `tests/api/test_audit.py`.

## Acceptance criteria

- [ ] Edit và mọi transition tạo snapshot/audit cùng transaction.
- [ ] approve immutable.
- [ ] concurrent edit một bên 409.
- [ ] GET không gọi VLM.
- [ ] migration giữ v1 snapshots và evidence refs.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/api/test_audit.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

Generation và edit snapshots; read không gọi VLM. Còn thiếu: Transition snapshots + real actor, immutable approved version reads. Source: [reports.py](../../backend/services/reports.py). Test fixture: [test_e2e.py](../../tests/api/test_e2e.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

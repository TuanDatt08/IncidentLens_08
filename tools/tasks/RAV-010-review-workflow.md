# RAV-010 — Engineer → Reviewer workflow

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: API, Frontend.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 04](../planning/sprints/sprint-04-review-workflow.md)

## Goal

Hoàn thành capability **Engineer → Reviewer workflow** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-REV-001](../specs/user-roles.md), [REQ-REV-002](../specs/user-roles.md), [REQ-REV-003](../specs/user-roles.md).

ADR: [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-005](../adrs/ADR-005-versioned-api-migration.md), [ADR-009](../adrs/ADR-009-report-versioning-and-audit.md).

Dependencies: [RAV-009](RAV-009-evidence-validation.md), [RAV-013](RAV-013-report-versioning-audit.md), [RAV-014](RAV-014-authentication-rbac.md), [RAV-016](RAV-016-api-v2-migration.md).

## Background / baseline evidence

`backend/services/review.py`: DRAFT submit/approve/reject, stale edit version; demo actor, rejected terminal. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

version-aware submit/reject/reopen/approve cho V2.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/review.py; api/reports.py; frontend/components/review/review-workspace.tsx.

Test: `tests/api/test_incident_workflow.py`.

## Acceptance criteria

- [x] Hai actor khác nhau.
- [x] stale version 409.
- [x] reject reason bắt buộc.
- [x] reopen tạo snapshot.
- [x] APPROVED immutable.
- [x] thiếu evidence không approve.
- [x] v1 rejected vẫn terminal.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/api/test_incident_workflow.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: HTTP hai actor, seven snapshots, stale409/selfreview403/rejectreason/reopen/immutableAPPROVED, missing asset approve422; V1 rejected-terminal regression giữ nguyên. Production identity dependency vẫn gated.

Evidence: [test_contracts_v2.py](../../tests/api/test_contracts_v2.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Submit/approve/reject reason/state, stale edit 409, demo audit có. Còn thiếu: Role thật, separate submitter/reviewer, reopen/transition snapshots. Source: [review.py](../../backend/services/review.py). Test fixture: [test_e2e.py](../../tests/api/test_e2e.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

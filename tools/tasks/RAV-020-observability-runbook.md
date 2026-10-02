# RAV-020 — Observability and release hardening

Status: **PARTIAL**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: API, Frontend.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 05](../planning/sprints/sprint-05-evaluation-hardening.md)

## Goal

Hoàn thành capability **Observability and release hardening** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-JOB-001](../specs/non-functional-requirements.md), [REQ-EVAL-002](../specs/evaluation.md).

ADR: [ADR-002](../adrs/ADR-002-background-job-processing.md), [ADR-010](../adrs/ADR-010-ai-evaluation-strategy.md).

Dependencies: [RAV-015](RAV-015-job-resume-budget.md).

## Background / baseline evidence

`backend/services/jobs.py`: pass/progress/error; CI backend có; thiếu stage cost metrics/production drills. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

JobStage metrics + sanitized trace/usage record.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/jobs.py; backend/worker.py; tools/docs/runbook.md.

Test: `tests/api/test_jobs.py`.

## Acceptance criteria

- [x] Stage/coverage/budget visible.
- [x] log không secret/raw PII.
- [x] failure drills worker/storage/provider/privacy.
- [ ] backup restore và retention policy.
- [ ] CI/backend + FE checks chạy.
- [x] release gate chưa đo vẫn blocked.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/api/test_jobs.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Stage ghi trước expensive work, coverage/budget/usage/provenance và sanitized error codes. Local worker/storage/provider/privacy failure fixtures đã chạy, SQLite backup/readback đã chạy; production PG restore/retention signoff/drill và remoteCI pending. CI thêm fullruff/Python/FE checks. Release gate giữ BLOCKED khi chưa đo.

Evidence: [test_worker_v2.py](../../tests/api/test_worker_v2.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

pass/progress/error + backend CI có. Còn thiếu: stage coverage/cost/usage metrics, frontend CI, PG/drills/retention. Source: [jobs.py](../../backend/services/jobs.py). Test fixture: [test_jobs.py](../../tests/api/test_jobs.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

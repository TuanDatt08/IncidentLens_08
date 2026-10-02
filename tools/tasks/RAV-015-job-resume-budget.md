# RAV-015 — Job checkpoints, resume and budgets

Status: **PARTIAL**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: API.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 02](../planning/sprints/sprint-02-incident-detection.md)

## Goal

Hoàn thành capability **Job checkpoints, resume and budgets** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-DET-002](../specs/incident-workflow.md), [REQ-JOB-001](../specs/non-functional-requirements.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-002](../adrs/ADR-002-background-job-processing.md).

Dependencies: [RAV-003](RAV-003-candidate-detection.md), [RAV-004](RAV-004-clip-extraction.md).

## Background / baseline evidence

`backend/services/jobs.py`, `worker.py`: PG lease/heartbeat/3 attempts; chưa segment checkpoint và budgets. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

checkpoint(job, segment, attempt), resume cursor và bounded budget.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/jobs.py; backend/worker.py; backend/models/tables.py.

Test: `tests/api/test_worker.py`.

## Acceptance criteria

- [x] Crash giữa segments resume không duplicate.
- [x] stale lease không publish.
- [x] max attempts/calls/disk/time hữu hạn.
- [x] partial result/coverage giữ.
- [ ] PostgreSQL multiworker smoke ngoài SQLite unit.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/api/test_worker.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Durable crash/resume không reanalyze report đã publish, stale lease/attempt fences, attempt-specific artifacts; pending discovery replacement, cancellation trước scan tiếp, per-artifact budget/manifest/telemetry guard, finite attempts/calls/wall. tests/api/test_jobs_v2.py + output_guard/resource_limits bổ sung. FFmpeg -fs không là OS hard quota; PostgreSQL multiworker chưa chạy do Docker daemon unavailable.

Evidence: [test_worker_v2.py](../../tests/api/test_worker_v2.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Lease heartbeat/3 attempts/reclaim/stale attempt fencing có. Còn thiếu: Segment checkpoint/resume/partial/cancel/budget. Source: [jobs.py](../../backend/services/jobs.py). Test fixture: [test_worker.py](../../tests/api/test_worker.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

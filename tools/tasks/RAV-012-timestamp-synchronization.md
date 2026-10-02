# RAV-012 — Timestamp synchronization

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: Frontend.

Role docs: [Backend](../../backend/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 01](../planning/sprints/sprint-01-foundation.md)

## Goal

Hoàn thành capability **Timestamp synchronization** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-SYNC-001](../specs/incident-workflow.md), [REQ-SYNC-002](../specs/incident-workflow.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-003](../adrs/ADR-003-evidence-first-analysis.md).

Dependencies: [RAV-002](RAV-002-log-normalization.md).

## Background / baseline evidence

`backend/services/processing.py`: collision offset mapping hiện có, chưa drift/quality/anchor verification. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

align(video_metadata, telemetry, anchors) -> TimeAlignment.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/synchronization.py; backend/services/processing.py.

Test: `tests/backend/test_services/test_synchronization.py`.

## Acceptance criteria

- [x] Offset/drift/residual lưu.
- [x] known anchors seek đúng trong tolerance fixture 100ms.
- [x] thiếu anchor ghi unknown.
- [x] không lẫn seconds tương đối va chạm với video_seconds.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_synchronization.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Offset/drift/residual/quality lưu, verified anchor mapping tolerance100ms; missing anchors UNKNOWN, collision-relative không silently video_seconds. FFmpeg seek được kiểm riêng trong extraction fixtures.

Evidence: [test_synchronization.py](../../tests/backend/test_services/test_synchronization.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Collision offset relative↔video conversion và bounds có. Còn thiếu: Anchor/drift/residual/quality + unknown alignment. Source: [video-time.ts](../../frontend/lib/video-time.ts). Test fixture: [test_processing.py](../../tests/backend/test_services/test_processing.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.

# RAV-003 — Candidate detection

Status: **TODO**

Delivery Status: **Todo**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 02](../planning/sprints/sprint-02-incident-detection.md)

## Goal

Hoàn thành capability **Candidate detection** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-DET-001](../specs/incident-workflow.md), [REQ-DET-002](../specs/incident-workflow.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-002](../adrs/ADR-002-background-job-processing.md).

Dependencies: [RAV-002](RAV-002-log-normalization.md), [RAV-012](RAV-012-timestamp-synchronization.md).

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

detect_candidates(telemetry, alignment, config) -> CandidateSet.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/candidate_detection.py; backend/services/processing.py.

Test: `tests/backend/test_services/test_candidate_detection.py`.

## Acceptance criteria

- [ ] Nhiều mốc phanh/đổi mode được đề cử.
- [ ] merge deterministic.
- [ ] window clamp.
- [ ] overflow UNANALYZED.
- [ ] fixture 5 giờ không chỉ có 5 frame.
- [ ] không có log dùng coverage-aware sparse scan.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_candidate_detection.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

Pass1 chỉ 5 frames và single candidate. Còn thiếu: Log/rule whole route, multi-window/sparse coverage/budget. Source: [processing.py](../../backend/services/processing.py). Test fixture: [test_processing.py](../../tests/backend/test_services/test_processing.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
